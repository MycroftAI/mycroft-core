# Copyright 2018 Mycroft AI Inc.
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
import os
from os.path import join, dirname, expanduser, exists
from time import sleep

import xdg.BaseDirectory

from ovos_utils.configuration import get_ovos_config, get_xdg_config_locations

# check for path overrides
_ovos_cfg = get_ovos_config()

DEFAULT_CONFIG = _ovos_cfg["default_config_path"] or \
                 join(dirname(__file__), "mycroft.conf")
SYSTEM_CONFIG = os.environ.get('MYCROFT_SYSTEM_CONFIG',
                               f'/etc/{_ovos_cfg["base_folder"]}/{_ovos_cfg["config_filename"]}')
# TODO: remove in 22.02
# Make sure we support the old location still
# Deprecated and will be removed eventually
OLD_USER_CONFIG = join(expanduser('~'), '.' + _ovos_cfg["base_folder"], _ovos_cfg["config_filename"])
USER_CONFIG = join(xdg.BaseDirectory.xdg_config_home, _ovos_cfg["base_folder"], _ovos_cfg["config_filename"])
REMOTE_CONFIG = "mycroft.ai"
WEB_CONFIG_CACHE = os.environ.get('MYCROFT_WEB_CACHE') or \
                   join(xdg.BaseDirectory.xdg_config_home, _ovos_cfg["base_folder"], 'web_cache.json')


def __ensure_folder_exists(path):
    """ Make sure the directory for the specified path exists.

        Args:
            path (str): path to config file
     """
    directory = dirname(path)
    if not exists(directory):
        try:
            os.makedirs(directory)
        except:
            sleep(0.2)
            if not exists(directory):
                try:
                    os.makedirs(directory)
                except Exception as e:
                    pass


__ensure_folder_exists(WEB_CONFIG_CACHE)
__ensure_folder_exists(USER_CONFIG)
