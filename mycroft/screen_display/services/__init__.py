from abc import ABCMeta, abstractmethod

__author__ = 'jarbas'


class DisplayBackend():
    """
        Base class for all display backend implementations.

        Args:
            config: configuration dict for the instance
            emitter: eventemitter or websocket object
    """
    __metaclass__ = ABCMeta

    @abstractmethod
    def __init__(self, config, emitter):
        pass

    @abstractmethod
    def display(self):
        """
           Display First Picture in Pictures List of paths
        """
        pass

    @abstractmethod
    def add_pictures(self, picture_list):
        """
          add pics
        """
        pass

    def reset(self):
        """
            Reset Display.
        """
        pass

    def clear(self):
        """
            Clear Display.
        """
        pass

    def next(self):
        """
            Skip to next pic in playlist.
        """
        pass

    def previous(self):
        """
            Skip to previous pic in playlist.
        """
        pass

    def lock(self):
        """
           Set Lock Flag so nothing else can display
        """
        pass

    def unlock(self):
        """
           Unset Lock Flag so nothing else can display
        """
        pass

    def change_fullscreen(self, value=True):
        """
           toogle fullscreen
        """
        pass

    def change_height(self, value=500):
        """
           change display height
        """
        pass

    def change_width(self, value=500):
        """
           change display width
        """
        pass

    def stop(self):
        """
            Stop display.
        """
        pass

    def close(self):
        self.stop()
