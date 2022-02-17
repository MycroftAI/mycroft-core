# Copyright 2019 Mycroft AI Inc.
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
from copy import deepcopy
from unittest.mock import Mock

from mycroft.configuration.config import LocalConf, DEFAULT_CONFIG

__CONFIG = LocalConf(DEFAULT_CONFIG)


class AnyCallable:
    """Class matching any callable.

    Useful for assert_called_with arguments.
    """
    def __eq__(self, other):
        return callable(other)


def base_config():
    """Base config used when mocking.

    Preload to skip hitting the disk each creation time but make a copy
    so modifications don't mutate it.

    Returns:
        (dict) Mycroft default configuration
    """
    return deepcopy(__CONFIG)


def mock_config(temp_dir):
    """Supply a reliable return value for the Configuration.get() method."""
    get_config_mock = Mock()
    config = base_config()
    config['skills']['priority_skills'] = ['foobar']
    config['data_dir'] = str(temp_dir)
    config['server']['metrics'] = False
    config['enclosure'] = {}

    get_config_mock.return_value = config
    return get_config_mock


class MessageBusMock:
    """Replaces actual message bus calls in unit tests.

    The message bus should not be running during unit tests so mock it
    out in a way that makes it easy to test code that calls it.
    """
    def __init__(self):
        self.message_types = []
        self.message_data = []
        self.event_handlers = []

    def emit(self, message):
        self.message_types.append(message.msg_type)
        self.message_data.append(message.data)

    def on(self, event, _):
        self.event_handlers.append(event)

    def once(self, event, _):
        self.event_handlers.append(event)
