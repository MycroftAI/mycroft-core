import time

from mycroft.messagebus.message import Message


class AudioService():
    def __init__(self, emitter):
        self.emitter = emitter
        self.emitter.on('MycroftAudioServiceTrackInfoReply', self._track_info)
        self.info = None

    def _track_info(self, message=None):
        self.info = message.metadata

    def play(self, tracks=[], utterance=''):
        self.emitter.emit(Message('MycroftAudioServicePlay',
                                  metadata={'tracks': tracks,
                                            'utterance': utterance}))

    def track_info(self):
        self.info = None
        self.emitter.emit(Message('MycroftAudioServiceTrackInfo'))
        while self.info is None:
            time.sleep(0.1)
        return self.info
