import subprocess
from time import sleep

from mycroft.audio.services import AudioBackend
from mycroft.messagebus.message import Message
from mycroft.util.log import LOG

__author__ = 'forslund'


class Mpg123Service(AudioBackend):
    """
        Audio backend for mpg123 player. This one is rather limited and
        only implements basic usage.
    """

    def __init__(self, config, emitter, name='mpg123'):
        self.config = config
        self.process = None
        self.emitter = emitter
        self.name = name
        self._stop_signal = False
        self._is_playing = False

        self.emitter.on('Mpg123ServicePlay', self._play)

    def supported_uris(self):
        return ['file', 'http']

    def clear_list(self):
        self.tracks = []

    def add_list(self, tracks):
        self.tracks = tracks
        LOG.info("Track list is " + str(tracks))

    def _play(self, message=None):
        """ Implementation specific async method to handle playback.
            This allows mpg123 service to use the "next method as well
            as basic play/stop.
        """
        LOG.info('Mpg123Service._play')
        self._is_playing = True
        track = self.tracks[self.index]

        # Replace file:// uri's with normal paths
        track = track.replace('file://', '')

        self.process = subprocess.Popen(['mpg123', track])
        # Wait for completion or stop request
        while self.process.poll() is None and not self._stop_signal:
            sleep(0.25)

        if self._stop_signal:
            self.process.terminate()
            self.process = None
            self._is_playing = False

            return
        self.index += 1
        # if there are more tracks available play next
        if self.index < len(self.tracks):
            self.emitter.emit(Message('Mpg123ServicePlay'))
        else:
            self._is_playing = False

    def play(self):
        LOG.info('Call Mpg123ServicePlay')
        self.index = 0
        self.emitter.emit(Message('Mpg123ServicePlay'))

    def stop(self):
        LOG.info('Mpg123ServiceStop')
        self._stop_signal = True
        while self._is_playing:
            sleep(0.1)
        self._stop_signal = False

    def pause(self):
        pass

    def resume(self):
        pass

    def next(self):
        # Terminate process to continue to next
        self.process.terminate()

    def previous(self):
        pass

    def lower_volume(self):
        pass

    def restore_volume(self):
        pass


def load_service(base_config, emitter):
    backends = base_config.get('backends', [])
    services = [(b, backends[b]) for b in backends
                if backends[b]['type'] == 'mpg123']
    instances = [Mpg123Service(s[1], emitter, s[0]) for s in services]
    return instances
