# Copyright 2017 Mycroft AI Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
from mycroft.audio.services import AudioBackend
from mycroft.util.log import LOG
try:
    from mpv import MPV
except ImportError:
    LOG.error("install mpv with "
              "pip install git+https://github.com/JarbasAl/python-mpv/")
    raise


class MPVService(AudioBackend):
    def __init__(self, config, emitter=None, name='mpv'):
        super(MPVService, self).__init__(config, emitter)
        self.player = MPV(ytdl=True)
        self.player['video'] = 'no'
        self.name = name
        self.tracks = []
        self.index = 0

    def track_start(self, data, other):
        if self._track_start_callback:
            self._track_start_callback(self.track_info()['name'])

    def supported_uris(self):
        return ['file', 'http', 'https']

    def clear_list(self):
        self.tracks = []

    def add_list(self, tracks):
        self.tracks += tracks
        LOG.info("Track list is " + str(self.tracks))

    def play(self):
        LOG.info('MpvService Play')
        if len(self.tracks):
            self.player.stop()
            self.player.play(self.tracks[self.index])
            self.player.wait_for_playback()
            self.next()

    def stop(self):
        LOG.info('MpvService Stop')
        self.clear_list()
        self.player.stop()

    def pause(self):
        LOG.info('MpvService Pause')
        self.player["pause"] = True

    def resume(self):
        LOG.info('MpvService Resume')
        self.player["pause"] = False

    def next(self):
        LOG.info('MpvService Next')
        self.index = self.index + 1
        if self.index > len(self.tracks):
            self.index = 0
        self.play()

    def previous(self):
        LOG.info('MpvService Previous')
        self.index = self.index - 1
        if self.index < 0:
            self.index = 0
        self.play()

    def lower_volume(self):
        pass

    def restore_volume(self):
        pass

    def track_info(self):
        ret = {"track": self.player["media-title"]}
        return ret

    def shutdown(self):
        self.player.terminate()


def load_service(base_config, emitter):
    backends = base_config.get('backends', [])
    services = [(b, backends[b]) for b in backends
                if backends[b]['type'] == 'mpv' and
                backends[b].get("active", True)]
    instances = [MPVService(s[1], emitter, s[0]) for s in services]
    return instances
