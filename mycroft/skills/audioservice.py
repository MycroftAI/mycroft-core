import time
from os.path import abspath
from mycroft.messagebus.message import Message


def ensure_uri(s):
    """
        Interprete paths as file:// uri's

        Args:
            s: string to be checked

        Returns:
            if s is uri, s is returned otherwise file:// is prepended
    """
    if '://' not in s:
        return 'file://' + abspath(s)
    else:
        return s


class AudioService():
    """
        AudioService object for interacting with the audio subsystem

        Args:
            emitter: eventemitter or websocket object
    """
    def __init__(self, emitter):
        self.emitter = emitter
        self.emitter.on('MycroftAudioServiceTrackInfoReply', self._track_info)
        self.info = None

    def _track_info(self, message=None):
        """
            Handler for catching returning track info
        """
        self.info = message.data

    def play(self, tracks=[], utterance=''):
        """ Start playback.

            Args:
                tracks: track uri or list of track uri's
                utterance: forward utterance for further processing by the
                           audio service.
        """
        if isinstance(tracks, basestring):
            tracks = [tracks]
        elif not isinstance(tracks, list):
            raise ValueError
        tracks = [ensure_uri(t) for t in tracks]
        self.emitter.emit(Message('MycroftAudioServicePlay',
                                  data={'tracks': tracks,
                                        'utterance': utterance}))

    def next(self):
        """ Change to next track. """
        self.emitter.emit(Message('MycroftAudioServiceNext'))

    def prev(self):
        """ Change to previous track. """
        self.emitter.emit(Message('MycroftAudioServicePrev'))

    def pause(self):
        """ Pause playback. """
        self.emitter.emit(Message('MycroftAudioServicePause'))

    def resume(self):
        """ Resume paused playback. """
        self.emitter.emit(Message('MycroftAudioServiceResume'))

    def track_info(self):
        """ Request information of current playing track.

            Returns:
                Dict with track info.
        """
        self.info = None
        self.emitter.emit(Message('MycroftAudioServiceTrackInfo'))
        while self.info is None:
            time.sleep(0.1)
        return self.info
