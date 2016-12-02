from mycroft.messagebus.message import Message


class AudioService():
    def __init__(self, emitter):
        self.emitter = emitter

    def play(self, tracks=[], utterance=''):
        self.emitter.emit(Message('MycroftAudioServicePlay',
                                  metadata={'tracks': tracks,
                                            'utterance': utterance}))

