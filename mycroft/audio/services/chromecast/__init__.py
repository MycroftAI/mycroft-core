from mycroft.messagebus.message import Message
from mycroft.util.log import getLogger
from mycroft.audio.services import AudioBackend
from os.path import dirname, abspath, basename
import sys
import time
from mimetypes import guess_type

import pychromecast

logger = getLogger(abspath(__file__).split('/')[-2])
__author__ = 'forslund'


class ChromecastService(AudioBackend):
    def _connect(self, message):
        logger.info('Trying to connect to chromecast')
        casts = pychromecast.get_chromecasts()
        if self.config is None or 'identifier' not in self.config:
            logger.error("Chromecast identifier not found!")
            return  # Can't connect since no id is specified
        else:
            identifier = self.config['identifier']
        for c in casts:
            if c.name == identifier:
                self.cast = c
                break
        else:
            logger.info('Couldn\'t find chromecast ' + identifier)
            self.connection_attempts += 1
            time.sleep(10)
            self.emitter.emit(Message('ChromecastServiceConnect'))
            return

        self.cast.quit_app()

    def __init__(self, config, emitter, name='chromecast', cast=None):
        self.connection_attempts = 0
        self.emitter = emitter
        self.config = config
        self.name = name

        self.tracklist = []

        if cast is not None:
            self.cast = cast
            self.cast.quit_app()
        else:
            self.cast = None
            self.emitter.on('ChromecastServiceConnect', self._connect)
            self.emitter.emit(Message('ChromecastServiceConnect'))

    def supported_uris(self):
        print "CHROMECAST FOUND: " + str(self.cast)
        if self.cast:
            return ['http', 'https']
        else:
            return []

    def clear_list(self):
        self.tracklist = []
        pass

    def add_list(self, tracks):
        self.tracklist = tracks
        pass

    def play(self):
        track = self.tracklist[0]
        print track, guess_type(track)
        mime = guess_type(track)[0] or 'audio/mp3'
        print mime
        self.cast.play_media(track, mime)

    def stop(self):
        self.cast.media_controller.stop()
        self.cast.quit_app()

    def pause(self):
        if not self.cast.media_controller.is_paused:
            self.cast.media_controller.pause()

    def resume(self):
        if self.cast.media_controller.is_paused:
            self.cast.media_controller.play()

    def next(self):
        pass

    def previous(self):
        pass

    def lower_volume(self):
        # self.cast.volume_down()
        pass

    def restore_volume(self):
        # self.cast.volume_up()
        pass

    def track_info(self):
        info = {}
        ret = {}
        ret['name'] = info.get('name', '')
        if 'album' in info:
            ret['artist'] = info['album']['artists'][0]['name']
            ret['album'] = info['album'].get('name', '')
        else:
            ret['artist'] = ''
            ret['album'] = ''
        return ret


def autodetect(config, emitter):
    casts = pychromecast.get_chromecasts()
    ret = []
    for c in casts:
        logger.info(c.name + " found.")
        ret.append(ChromecastService(config, emitter, c.name.lower(), c))

    return ret
