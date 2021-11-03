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

from mycroft.api import STTApi, HTTPError
from mycroft.configuration import Configuration
from mycroft.util.log import LOG

from ovos_plugin_manager.stt import OVOSSTTFactory, load_stt_plugin
from ovos_plugin_manager.templates.stt import STT, TokenSTT, GoogleJsonSTT, \
    StreamingSTT, StreamThread, BasicSTT, KeySTT


def requires_pairing(func):
    """Decorator kicking of pairing sequence if client is not allowed access.

    Checks the http status of the response if an HTTP error is recieved. If
    a 401 status is detected returns "pair my device" to trigger the pairing
    skill.
    """

    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except HTTPError as e:
            if e.response.status_code == 401:
                LOG.warning('Access Denied at mycroft.ai')
                # phrase to start the pairing process
                return 'pair my device'
            else:
                raise

    return wrapper


class MycroftSTT(STT):
    """Default mycroft STT."""

    def __init__(self):
        super(MycroftSTT, self).__init__()
        self.api = STTApi("stt")

    @requires_pairing
    def execute(self, audio, language=None):
        self.lang = language or self.lang
        try:
            return self.api.stt(audio.get_flac_data(convert_rate=16000),
                                self.lang, 1)[0]
        except Exception:
            return self.api.stt(audio.get_flac_data(), self.lang, 1)[0]


class STTFactory(OVOSSTTFactory):
    @staticmethod
    def create():
        config = Configuration.get().get("stt", {})
        module = config.get("module", "mycroft")
        if module == "mycroft":
            return MycroftSTT()
        return OVOSSTTFactory.create(config)
