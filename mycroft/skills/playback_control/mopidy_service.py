from mycroft.messagebus.message import Message
from mycroft.util.log import getLogger
from os.path import dirname, abspath, basename
import sys
import time

logger = getLogger(abspath(__file__).split('/')[-2])
__author__ = 'forslund'

sys.path.append(abspath(dirname(__file__)))
Mopidy = __import__('mopidypost').Mopidy

class MopidyService():
    def _connect(self, message):
        logger.debug('Could not connect to server, will retry quietly')
        url = 'http://localhost:6680'
        if self.config is not None:
            url = self.config.get('url', url)
        try:
            self.mopidy = Mopidy(url)
        except:
            if self.connection_attempts < 1:
                logger.debug('Could not connect to server, will retry quietly')
            self.connection_attempts += 1
            time.sleep(10)
            self.emitter.emit(Message('MopidyServiceConnect'))
            return

        logger.info('Connected to mopidy server')
    
    def __init__(self, config, emitter, name='mopidy'):
        self.connection_attempts = 0
        self.emitter = emitter
        self.config = config
        self.name = name

        self.mopidy = None
        self.emitter.on('MopidyServiceConnect', self._connect)
        self._connect(None)

    def supported_uris(self):
        if self.mopidy:
            return ['file', 'http', 'https', 'local', 'spotify', 'gmusic']
        else:
            return []

    def clear_list(self):
        self.mopidy.clear_list()
    
    def add_list(self, tracks):
        self.mopidy.add_list(tracks)

    def play(self):
        self.mopidy.play()

    def stop(self):
        self.mopidy.clear_list()
        self.mopidy.stop()

    def pause(self):
        self.mopidy.pause()

    def resume(self):
        self.mopidy.resume()

    def next(self):
        self.mopidy.next()

    def previous(self):
        self.mopidy.previous()

    def lower_volume(self):
        self.mopidy.lower_volume()

    def restore_volume(self):
        self.mopidy.restore_volume()

    def track_info(self):
        info = self.mopidy.currently_playing()
        ret = {}
        ret['name'] = info.get('name', '')
        if 'album' in info:
            ret['artist'] = info['album']['artists'][0]['name']
            ret['album'] = info['album'].get('name', '')
        else:
            ret['artist'] = ''
            ret['album'] = ''
        return ret

