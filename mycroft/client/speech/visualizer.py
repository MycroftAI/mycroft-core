import pyaudio
from threading import Thread, Lock
from mycroft.configuration import Configuration
from mycroft.util.log import LOG
from mycroft.messagebus.message import Message
from .volume_listener import (get_rms, open_mic_stream, read_file_from,
                              INPUT_FRAMES_PER_BLOCK)


class VolumeVisualizer:
    def __init__(self):
        self.bus = None
        self.config_core = Configuration.get()
        self.running = False
        self.thread = None
        self.pa = pyaudio.PyAudio()
        try:
            self.listener_file = os.path.join(get_ipc_directory(), 'mic_level')
            self.st_results = os.stat(self.listener_file)
        except Exception:
            self.listener_file = None
            self.st_results = None
        self.max_amplitude = 0.001

    def setup_mic_listening(self):
        """ Initializes PyAudio, starts an input stream and launches the
            listening thread.
        """
        listener_conf = self.config_core['listener']
        self.stream = open_mic_stream(self.pa,
                                      listener_conf.get('device_index'),
                                      listener_conf.get('device_name'))
        self.amplitude = 0

    def start_listening_thread(self):
        # Start listening thread
        if not self.thread:
            self.running = True
            self.thread = Thread(target=self.listen_thread)
            self.thread.daemon = True
            self.thread.start()

    def stop_listening_thread(self):
        if self.thread:
            self.running = False
            self.thread.join()
            self.thread = None

    def listen_thread(self):
        """ listen on mic input until self.running is False. """
        self.setup_mic_listening()
        LOG.debug("Starting listening")
        while(self.running):
            self.listen()
        self.stream.close()
        LOG.debug("Listening stopped")

    def get_audio_level(self):
        """ Get level directly from audio device. """
        try:
            block = self.stream.read(INPUT_FRAMES_PER_BLOCK)
        except IOError as e:
            # damn
            self.errorcount += 1
            LOG.error('{} Error recording: {}'.format(self.errorcount, e))
            return None

        amplitude = get_rms(block)
        result = int(amplitude / ((self.max_amplitude) + 0.001) * 15)
        self.max_amplitude = max(amplitude, self.max_amplitude)
        return result

    def get_listener_level(self):
        """ Get level from IPC file created by listener. """
        time.sleep(0.05)
        if not self.listener_file:
            try:
                self.listener_file = os.path.join(get_ipc_directory(),
                                                  'mic_level')
            except FileNotFoundError:
                return None

        try:
            st_results = os.stat(self.listener_file)

            if (not st_results.st_ctime == self.st_results.st_ctime or
                    not st_results.st_mtime == self.st_results.st_mtime):
                ret = read_file_from(self.listener_file, 0)
                self.st_results = st_results
                if ret is not None:
                    if ret > self.max_amplitude:
                        self.max_amplitude = ret
                    ret = int(ret / self.max_amplitude * 10)
                return ret
        except Exception as e:
            LOG.error(repr(e))
        return None

    def listen(self):
        """ Read microphone level and send rms. """
        amplitude = self.get_audio_level()
        self.bus.emit(Message("gui.value.set",
                              data={"__from": "system.speech.visualizer",
                                    "state": "listening",
                                    "volume": amplitude}))

    def handle_listener_started(self, bus=None):
        """ Shows listener page after wakeword is triggered.
            Starts countdown to show the idle page.
        """
        # Set the bus
        self.bus = bus

        # Start idle timer
        self.bus.emit(Message("mycroft.device.start_weak.idle"))

        # Lower the max by half at the start of listener to make sure
        # loud noices doesn't make the level stick to much
        if self.max_amplitude > 0.001:
            self.max_amplitude /= 2

        self.start_listening_thread()

    def handle_listener_ended(self):
        self.stop_listening_thread()
