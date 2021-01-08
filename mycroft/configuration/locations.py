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
from xdg import BaseDirectory

DEFAULT_CONFIG = join(dirname(__file__), 'mycroft.conf')
SYSTEM_CONFIG = os.environ.get('MYCROFT_SYSTEM_CONFIG',
                               '/etc/mycroft/mycroft.conf')
# Make sure we support the old location still
# Deprecated and will be removed eventually
OLD_USER_CONFIG = join(expanduser('~'), '.mycroft/mycroft.conf')
USER_CONFIG = join(BaseDirectory.save_config_path('mycroft'),
                   'mycroft.conf')
