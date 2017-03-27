from abc import ABCMeta, abstractmethod

__author__ = 'forslund'


class AudioBackend():
    __metaclass__ = ABCMeta

    @abstractmethod
    def __init__(self, config, emitter):
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

    def pause(self):
        pass

    def resume(self):
        pass

    def next(self):
        pass

    def previous(self):
        pass

    def lower_volume(self):
        pass

    def restore_volume(self):
        pass

    def track_info(self):
        pass
