from os.path import dirname, abspath, basename
from mycroft.audio.services import AudioBackend
from mycroft.util.log import getLogger
import vlc

logger = getLogger(abspath(__file__).split('/')[-2])


class VlcService(AudioBackend):
    def __init__(self, config, emitter=None, name='vlc'):
        self.instance = vlc.Instance()
        self.list_player = self.instance.media_list_player_new()
        self.player = self.instance.media_player_new()
        self.list_player.set_media_player(self.player)

        self.config = config
        self.emitter = emitter
        self.name = name
        self.normal_volume = None

    def supported_uris(self):
        return ['file', 'http']

    def clear_list(self):
        empty = self.instance.media_list_new()
        self.list_player.set_media_list(empty)

    def add_list(self, tracks):
        logger.info("Track list is " + str(tracks))
        vlc_tracks = self.instance.media_list_new()
        for t in tracks:
            vlc_tracks.add_media(self.instance.media_new(t))
        self.list_player.set_media_list(vlc_tracks)

    def play(self):
        logger.info('VLCService Play')
        self.list_player.play()

    def stop(self):
        logger.info('VLCService Stop')
        self.clear_list()
        self.list_player.stop()

    def pause(self):
        self.player.set_pause(1)

    def resume(self):
        self.player.set_pause(0)

    def next(self):
        self.list_player.next()

    def previous(self):
        self.list_player.previous()

    def lower_volume(self):
        if self.normal_volume is None:
            self.normal_volume = self.player.audio_get_volume()
            self.player.audio_set_volume(self.normal_volume / 5)

    def restore_volume(self):
        if self.normal_volume:
            self.player.audio_set_volume(self.normal_volume)
            self.normal_volume = None

    def track_info(self):
        ret = {}
        meta = vlc.Meta
        t = self.player.get_media()
        ret['album'] = t.get_meta(meta.Album)
        ret['artists'] = [t.get_meta(meta.Artist)]
        ret['name'] = t.get_meta(meta.Title)
        return ret


def load_service(base_config, emitter):
    backends = base_config.get('backends', [])
    services = [(b, backends[b]) for b in backends
                if backends[b]['type'] == 'vlc']
    instances = [VlcService(s[1], emitter, s[0]) for s in services]
    return instances
