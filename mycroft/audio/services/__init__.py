from abc import ABCMeta, abstractmethod

__author__ = 'forslund'


class AudioBackend():
    """
        Base class for all audio backend implementations.

        Args:
            config: configuration dict for the instance
            emitter: eventemitter or websocket object
    """
    __metaclass__ = ABCMeta

    @abstractmethod
    def __init__(self, config, emitter):
        pass

    @abstractmethod
    def supported_uris(self):
        """
            Returns: list of supported uri types.
        """
        pass

    @abstractmethod
    def clear_list(self):
        """
            Clear playlist
        """
        pass

    @abstractmethod
    def add_list(self, tracks):
        """
            Add tracks to backend's playlist.

            Args:
                tracks: list of tracks.
        """
        pass

    @abstractmethod
    def play(self):
        """
            Start playback.
        """
        pass

    @abstractmethod
    def stop(self):
        """
            Stop playback.
        """
        pass

    def pause(self):
        """
            Pause playback.
        """
        pass

    def resume(self):
        """
            Resume paused playback.
        """
        pass

    def next(self):
        """
            Skip to next track in playlist.
        """
        pass

    def previous(self):
        """
            Skip to previous track in playlist.
        """
        pass

    def lower_volume(self):
        """
            Lower volume.
        """
        pass

    def restore_volume(self):
        """
            Restore normal volume.
        """
        pass

    def track_info(self):
        """
            Fetch info about current playing track.

            Returns:
                Dict with track info.
        """
        pass
