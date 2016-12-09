from abc import ABCMeta, abstractmethod
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


class AudioBackend():
    __metaclass__ = ABCMeta
    @abstractmethod
    def __init__(self, config, emitter):
        pass

    @property
    @abstractmethod
    def name(self):
        pass

    @abstractmethod
    def supported_uris(self):
        pass

    @abstractmethod
    def clear_list(self):
        pass

    @abstractmethod
    def add_list(self, tracks):
        pass

    @abstractmethod
    def play(self):
        pass

    @abstractmethod
    def stop(self):
        pass

    @abstractmethod
    def pause(self):
        pass

    @abstractmethod
    def resume(self):
        pass

    @abstractmethod
    def next(self):
        pass

    @abstractmethod
    def previous(self):
        pass

    @abstractmethod
    def lower_volume(self):
        pass

    @abstractmethod
    def restore_volume(self):
        pass

    @abstractmethod
    def track_info(self):
        pass
