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
from mycroft.configuration.config import Configuration, LocalConf, RemoteConf
from mycroft.configuration.locale import set_default_lf_lang, setup_locale, \
    set_default_tz, set_default_lang, get_default_tz, get_default_lang, \
    get_config_tz, get_primary_lang_code, load_languages, load_language
from mycroft.configuration.locations import SYSTEM_CONFIG, USER_CONFIG, \
    get_xdg_config_locations, BASE_FOLDER, DEFAULT_CONFIG
from mycroft.configuration.ovos import is_using_xdg, get_ovos_config
