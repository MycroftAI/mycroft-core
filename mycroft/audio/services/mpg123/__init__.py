import subprocess
from mycroft.audio.services import AudioBackend
from mycroft.util.log import getLogger
from mycroft.messagebus.message import Message

from os.path import abspath

__author__ = 'forslund'

logger = getLogger(abspath(__file__).split('/')[-2])


class Mpg123Service(AudioBackend):
    def __init__(self, config, emitter, name='mpg123'):
        self.config = config
        self.process = None
        self.emitter = emitter
        self.name = name

        self.emitter.on('Mpg123ServicePlay', self._play)

    def supported_uris(self):
        return ['file', 'http']

    def clear_list(self):
        self.tracks = []

    def add_list(self, tracks):
        self.tracks = tracks
        logger.info("Track list is " + str(tracks))

    def _play(self, message=None):
        logger.info('Mpg123Service._play')
        track = self.tracks[self.index]
        self.process = subprocess.Popen(['mpg123', track])
        self.process.communicate()
        self.process = None
        self.index += 1
        if self.index >= len(self.tracks):
            self.emitter.emit(Message('Mpg123ServicePlay'))

    def play(self):
        logger.info('Call Mpg123ServicePlay')
        self.index = 0
        self.emitter.emit(Message('Mpg123ServicePlay'))

    def stop(self):
        logger.info('Mpg123ServiceStop')
        self.clear_list()
        if self.process:
            self.process.terminate()
            self.process = None

    def pause(self):
        pass

    def resume(self):
        pass

    def next(self):
        self.process.terminate()

    def previous(self):
        pass

    def lower_volume(self):
        pass

    def restore_volume(self):
        pass

    def track_info(self):
        return {}


def load_service(base_config, emitter):
    backends = base_config.get('backends', [])
    services = [(b, backends[b]) for b in backends
                if backends[b]['type'] == 'mpg123']
    instances = [Mpg123Service(s[1], emitter, s[0]) for s in services]
    return instances
