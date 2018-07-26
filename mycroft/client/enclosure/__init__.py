# Copyright 2017 Mycroft AI Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
import subprocess
import time
from alsaaudio import Mixer
from threading import Thread, Timer

import serial

import mycroft.dialog
from mycroft.api import has_been_paired
from mycroft.enclosure import Enclosure
from mycroft.client.enclosure.display_manager import \
    initiate_display_manager_ws
from mycroft.configuration.config import Configuration, LocalConf, USER_CONFIG
from mycroft.messagebus.client.ws import WebsocketClient
from mycroft.messagebus.message import Message
from mycroft.util import play_wav, create_signal, connected, \
    wait_while_speaking, check_for_signal
from mycroft.util.audio_test import record
from mycroft.util.log import LOG
from queue import Queue

from mycroft.client.enclosure.arduino import EnclosureArduino
from mycroft.client.enclosure.eyes import EnclosureEyes
from mycroft.client.enclosure.mouth import EnclosureMouth
from mycroft.client.enclosure.weather import EnclosureWeather


class EnclosureReader(Thread):
    """
    Reads data from Serial port.

    Listens to all commands sent by Arduino that must be be performed on
    Mycroft Core.

    E.g. Mycroft Stop Feature
        #. Arduino sends a Stop command after a button press on a Mycroft unit
        #. ``EnclosureReader`` captures the Stop command
        #. Notify all Mycroft Core processes (e.g. skills) to be stopped

    Note: A command is identified by a line break
    """

    def __init__(self, serial, ws, lang=None):
        super(EnclosureReader, self).__init__(target=self.read)
        self.alive = True
        self.daemon = True
        self.serial = serial
        self.ws = ws
        self.lang = lang or 'en-us'
        self.start()

        # Notifications from mycroft-core
        self.ws.on("mycroft.stop.handled", self.on_stop_handled)

    def read(self):
        while self.alive:
            try:
                data = self.serial.readline()[:-2]
                if data:
                    self.process(data.decode())
            except Exception as e:
                LOG.error("Reading error: {0}".format(e))

    def on_stop_handled(self, event):
        # A skill performed a stop
        check_for_signal('buttonPress')

    def process(self, data):
        # TODO: Look into removing this emit altogether.
        # We need to check if any other serial bus messages
        # are handled by other parts of the code
        if "mycroft.stop" not in data:
            self.ws.emit(Message(data))

        if "Command: system.version" in data:
            # This happens in response to the "system.version" message
            # sent during the construction of Enclosure()
            self.ws.emit(Message("enclosure.started"))

        if "mycroft.stop" in data:
            if has_been_paired():
                create_signal('buttonPress')
                self.ws.emit(Message("mycroft.stop"))

        if "volume.up" in data:
            self.ws.emit(Message("mycroft.volume.increase",
                                 {'play_sound': True}))

        if "volume.down" in data:
            self.ws.emit(Message("mycroft.volume.decrease",
                                 {'play_sound': True}))

        if "system.test.begin" in data:
            self.ws.emit(Message('recognizer_loop:sleep'))

        if "system.test.end" in data:
            self.ws.emit(Message('recognizer_loop:wake_up'))

        if "mic.test" in data:
            mixer = Mixer()
            prev_vol = mixer.getvolume()[0]
            mixer.setvolume(35)
            self.ws.emit(Message("speak", {
                'utterance': "I am testing one two three"}))

            time.sleep(0.5)  # Prevents recording the loud button press
            record("/tmp/test.wav", 3.0)
            mixer.setvolume(prev_vol)
            play_wav("/tmp/test.wav").communicate()

            # Test audio muting on arduino
            subprocess.call('speaker-test -P 10 -l 0 -s 1', shell=True)

        if "unit.shutdown" in data:
            # Eyes to soft gray on shutdown
            self.ws.emit(Message("enclosure.eyes.color",
                                 {'r': 70, 'g': 65, 'b': 69}))
            self.ws.emit(
                Message("enclosure.eyes.timedspin",
                        {'length': 12000}))
            self.ws.emit(Message("enclosure.mouth.reset"))
            time.sleep(0.5)  # give the system time to pass the message
            self.ws.emit(Message("system.shutdown"))

        if "unit.reboot" in data:
            # Eyes to soft gray on reboot
            self.ws.emit(Message("enclosure.eyes.color",
                                 {'r': 70, 'g': 65, 'b': 69}))
            self.ws.emit(Message("enclosure.eyes.spin"))
            self.ws.emit(Message("enclosure.mouth.reset"))
            time.sleep(0.5)  # give the system time to pass the message
            self.ws.emit(Message("system.reboot"))

        if "unit.setwifi" in data:
            self.ws.emit(Message("system.wifi.setup", {'lang': self.lang}))

        if "unit.factory-reset" in data:
            self.ws.emit(Message("speak", {
                'utterance': mycroft.dialog.get("reset to factory defaults")}))
            subprocess.call(
                'rm ~/.mycroft/identity/identity2.json',
                shell=True)
            self.ws.emit(Message("system.wifi.reset"))
            self.ws.emit(Message("system.ssh.disable"))
            wait_while_speaking()
            self.ws.emit(Message("enclosure.mouth.reset"))
            self.ws.emit(Message("enclosure.eyes.spin"))
            self.ws.emit(Message("enclosure.mouth.reset"))
            time.sleep(5)  # give the system time to process all messages
            self.ws.emit(Message("system.reboot"))

        if "unit.enable-ssh" in data:
            # This is handled by the wifi client
            self.ws.emit(Message("system.ssh.enable"))
            self.ws.emit(Message("speak", {
                'utterance': mycroft.dialog.get("ssh enabled")}))

        if "unit.disable-ssh" in data:
            # This is handled by the wifi client
            self.ws.emit(Message("system.ssh.disable"))
            self.ws.emit(Message("speak", {
                'utterance': mycroft.dialog.get("ssh disabled")}))

        if "unit.enable-learning" in data or "unit.disable-learning" in data:
            enable = 'enable' in data
            word = 'enabled' if enable else 'disabled'

            LOG.info("Setting opt_in to: " + word)
            new_config = {'opt_in': enable}
            user_config = LocalConf(USER_CONFIG)
            user_config.merge(new_config)
            user_config.store()

            self.ws.emit(Message("speak", {
                'utterance': mycroft.dialog.get("learning " + word)}))

    def stop(self):
        self.alive = False


class EnclosureWriter(Thread):
    """
    Writes data to Serial port.
        #. Enqueues all commands received from Mycroft enclosures
           implementation
        #. Process them on the received order by writing on the Serial port

    E.g. Displaying a text on Mycroft's Mouth
        #. ``EnclosureMouth`` sends a text command
        #. ``EnclosureWriter`` captures and enqueue the command
        #. ``EnclosureWriter`` removes the next command from the queue
        #. ``EnclosureWriter`` writes the command to Serial port

    Note: A command has to end with a line break
    """

    def __init__(self, serial, ws, size=16):
        super(EnclosureWriter, self).__init__(target=self.flush)
        self.alive = True
        self.daemon = True
        self.serial = serial
        self.ws = ws
        self.commands = Queue(size)
        self.start()

    def flush(self):
        while self.alive:
            try:
                cmd = self.commands.get() + '\n'
                self.serial.write(cmd.encode())
                self.commands.task_done()
            except Exception as e:
                LOG.error("Writing error: {0}".format(e))

    def write(self, command):
        self.commands.put(str(command))

    def stop(self):
        self.alive = False


class Mark1Enclosure(Enclosure):
    """
    Serves as a communication interface between Arduino and Mycroft Core.

    ``Enclosure`` initializes and aggregates all enclosures implementation.

    E.g. ``EnclosureEyes``, ``EnclosureMouth`` and ``EnclosureArduino``

    It also listens to the basis events in order to perform those core actions
    on the unit.

    E.g. Start and Stop talk animation
    """

    _last_internet_notification = 0

    def __init__(self):
        self.ws = WebsocketClient()
        super(Mark1Enclosure, self).__init__(self.ws, "Mark1")

        Configuration.init(self.ws)

        global_config = Configuration.get()
        self.lang = global_config['lang']
        self.config = global_config.get("enclosure")

        self.__init_serial()
        self.reader = EnclosureReader(self.serial, self.ws, self.lang)
        self.writer = EnclosureWriter(self.serial, self.ws)

        # Prepare to receive message when the Arduino responds to the
        # following "system.version"
        self.ws.on("enclosure.started", self.on_arduino_responded)
        self.arduino_responded = False
        # Send a message to the Arduino across the serial line asking
        # for a reply with version info.
        self.writer.write("system.version")
        # Start a 5 second timer.  If the serial port hasn't received
        # any acknowledgement of the "system.version" within those
        # 5 seconds, assume there is nothing on the other end (e.g.
        # we aren't running a Mark 1 with an Arduino)
        Timer(5, self.check_for_response).start()

        # initiates the web sockets on display manager
        # NOTE: this is a temporary place to initiate display manager sockets
        initiate_display_manager_ws()

    def on_arduino_responded(self, event=None):
        self.eyes = EnclosureEyes(self.writer)
        self.mouth = EnclosureMouth(self.writer)
        self.system = EnclosureArduino(self.writer)
        self.weather = EnclosureWeather(self.writer)
        self.reset()
        self.arduino_responded = True

        # verify internet connection and prompt user on bootup if needed
        if not connected():
            # We delay this for several seconds to ensure that the other
            # clients are up and connected to the messagebus in order to
            # receive the "speak".  This was sometimes happening too
            # quickly and the user wasn't notified what to do.
            Timer(5, self._do_net_check).start()

    def on_no_internet(self, message=None):
        if connected():
            # One last check to see if connection was established
            return

        if time.time() - Mark1Enclosure._last_internet_notification < 30:
            # don't bother the user with multiple notifications with 30 secs
            return

        Mark1Enclosure._last_internet_notification = time.time()

        if has_been_paired():
            # Handle the translation within that code.
            self.ws.emit(Message("speak", {
                'utterance': "This device is not connected to the Internet. "
                             "Either plug in a network cable or hold the "
                             "button on top for two seconds, then select "
                             "wifi from the menu"}))
        else:
            # enter wifi-setup mode automatically
            self.ws.emit(Message('system.wifi.setup', {'lang': self.lang}))

    def system_reset(self, message=None):
        self.system.reset()

    def system_mute(self, message=None):
        self.system.mute()

    def system_unmute(self, message=None):
        self.system.unmute()

    def system_blink(self, message=None):
        times = 1
        if message and message.data:
            times = message.data.get("times", times)
        self.system.blink(times)

    def eyes_on(self, message=None):
        self.eyes.on()

    def eyes_off(self, message=None):
        self.eyes.off()

    def eyes_blink(self, message=None):
        side = "b"
        if message and message.data:
            side = message.data.get("side", side)
        self.eyes.blink(side)

    def eyes_narrow(self, message=None):
        self.eyes.narrow()

    def eyes_look(self, message=None):
        if message and message.data:
            side = message.data.get("side", "")
            self.eyes.look(side)

    def eyes_color(self, message=None):
        r, g, b = 255, 255, 255
        if message and message.data:
            r = int(message.data.get("r", r))
            g = int(message.data.get("g", g))
            b = int(message.data.get("b", b))
        color = (r * 65536) + (g * 256) + b
        self.eyes.color(color)

    def eyes_brightness(self, message=None):
        level = 30
        if message and message.data:
            level = message.data.get("level", level)
        self.eyes.brightness(level)

    def eyes_volume(self, message=None):
        volume = 4
        if message and message.data:
            volume = message.data.get("volume", volume)
        self.eyes.volume(volume)

    def eyes_reset(self, message=None):
        self.eyes.reset()

    def eyes_spin(self, message=None):
        self.eyes.spin()

    def eyes_timed_spin(self, message=None):
        length = 5000
        if message and message.data:
            length = message.data.get("length", length)
        self.eyes.timed_spin(length)

    def eyes_set_pixel(self, message=None):
        idx = 0
        r, g, b = 255, 255, 255
        if message and message.data:
            idx = int(message.data.get("idx", idx))
            r = int(message.data.get("r", r))
            g = int(message.data.get("g", g))
            b = int(message.data.get("b", b))
        color = (r * 65536) + (g * 256) + b
        self.eyes.set_pixel(idx, color)

    def eyes_fill(self, message=None):
        amount = 0
        if message and message.data:
            percent = int(message.data.get("percentage", 0))
            amount = int(round(23.0 * percent / 100.0))
        self.eyes.fill(amount)

    def mouth_reset(self, message=None):
        self.mouth.reset()

    def mouth_talk(self, message=None):
        self.mouth.talk()

    def mouth_think(self, message=None):
        self.mouth.think()

    def mouth_listen(self, message=None):
        self.mouth.listen()

    def mouth_smile(self, message=None):
        self.mouth.smile()

    def mouth_viseme(self, message=None):
        if message and message.data:
            code = message.data.get("code")
            time_until = message.data.get("until")
            self.mouth.viseme(code, time_until)

    def mouth_text(self, message=None):
        text = ""
        if message and message.data:
            text = message.data.get("text", text)
        self.mouth.text(text)

    def activate_mouth_events(self, message=None):
        self.ws.on('recognizer_loop:record_begin', self.mouth.listen)
        self.ws.on('recognizer_loop:record_end', self.mouth.reset)
        self.ws.on('recognizer_loop:audio_output_start', self.mouth.talk)
        self.ws.on('recognizer_loop:audio_output_end', self.mouth.reset)

    def deactivate_mouth_events(self, message=None):
        self.ws.remove('recognizer_loop:record_begin', self.mouth.listen)
        self.ws.remove('recognizer_loop:record_end', self.mouth.reset)
        self.ws.remove('recognizer_loop:audio_output_start',
                       self.mouth.talk)
        self.ws.remove('recognizer_loop:audio_output_end',
                       self.mouth.reset)

    def mouth_display(self, message=None):
        code = ""
        xOffset = ""
        yOffset = ""
        clearPrevious = ""
        if message and message.data:
            code = message.data.get("img_code", code)
            xOffset = message.data.get("xOffset", xOffset)
            yOffset = message.data.get("yOffset", yOffset)
            clearPrevious = message.data.get("clearPrev", clearPrevious)
        self.mouth.display(code, xOffset, yOffset, clearPrevious)

    def weather_display(self, message=None):
        img_code = message.data.get("img_code", None)
        temp = message.data.get("temp", None)
        self.weather.display(img_code, temp)

    def __init_serial(self):
        try:
            self.port = self.config.get("port")
            self.rate = self.config.get("rate")
            self.timeout = self.config.get("timeout")
            self.serial = serial.serial_for_url(
                url=self.port, baudrate=self.rate, timeout=self.timeout)
            LOG.info("Connected to: %s rate: %s timeout: %s" %
                     (self.port, self.rate, self.timeout))
        except:
            LOG.error("Impossible to connect to serial port: "+str(self.port))
            raise

    def reset(self, message=None):
        # Reset both the mouth and the eye elements to indicate the unit is
        # ready for input.
        self.writer.write("eyes.reset")
        self.writer.write("mouth.reset")

    def speak(self, text):
        self.ws.emit(Message("speak", {'utterance': text}))

    def run(self):
        try:
            self.ws.run_forever()
        except Exception as e:
            LOG.error("Error: {0}".format(e))
            self.shutdown()

    def check_for_response(self):
        if not self.arduino_responded:
            # There is nothing on the other end of the serial port
            # close these serial-port readers and this process
            self.writer.stop()
            self.reader.stop()
            self.serial.close()
            self.ws.close()

    def _handle_pairing_complete(self, Message):
        """
            Handler for 'mycroft.paired', unmutes the mic after the pairing is
            complete.
        """
        self.ws.emit(Message("mycroft.mic.unmute"))

    def _do_net_check(self):
        LOG.info("Checking internet connection")
        if not connected():  # and self.conn_monitor is None:
            if has_been_paired():
                # TODO: Enclosure/localization
                self.speak("This unit is not connected to the Internet. "
                           "Either plug in a network cable or hold the "
                           "button on top for two seconds, then select "
                           "wifi from the menu")
            else:
                # Begin the unit startup process, this is the first time it
                # is being run with factory defaults.

                # TODO: Enclosure/localization

                # Don't listen to mic during this out-of-box experience
                self.ws.emit(Message("mycroft.mic.mute"))
                # Setup handler to unmute mic at the end of on boarding
                # i.e. after pairing is complete
                self.ws.once('mycroft.paired', self._handle_pairing_complete)

                self.speak(mycroft.dialog.get('mycroft.intro'))
                wait_while_speaking()
                time.sleep(2)  # a pause sounds better than just jumping in

                # Kick off wifi-setup automatically
                data = {'allow_timeout': False, 'lang': self.lang}
                self.ws.emit(Message('system.wifi.setup', data))
