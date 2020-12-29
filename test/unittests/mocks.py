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

from msm import MycroftSkillsManager
from msm.skill_repo import SkillRepo

from mycroft.configuration.config import LocalConf, DEFAULT_CONFIG

__CONFIG = LocalConf(DEFAULT_CONFIG)


def base_config():
    """Base config used when mocking.

    Preload to skip hitting the disk each creation time but make a copy
    so modifications don't mutate it.

    Returns:
        (dict) Mycroft default configuration
    """
    return deepcopy(__CONFIG)


def mock_msm(temp_dir):
    """Mock the MycroftSkillsManager because it reaches out to the internet."""
    msm_mock = Mock(spec=MycroftSkillsManager)
    msm_mock.skills_dir = str(temp_dir)
    msm_mock.platform = 'test_platform'
    msm_mock.lock = Mock()
    msm_mock.repo = Mock(spec=SkillRepo)
    msm_mock.repo.get_default_skill_names = Mock(return_value=[
        ('default', ['time', 'weather']),
        ('test_platform', ['test_skill'])
    ])
    msm_mock.device_skill_state = dict(
        skills=[
            dict(name='test_skill', beta=False)
        ]
    )
    skill = Mock()
    skill.is_local = True
    skill.path = str(temp_dir)
    skill.skill_gid = 'test_skill|99.99'
    skill.meta_info = dict(display_name='Test Skill')
    msm_mock.list_all_defaults.return_value = [skill]
    msm_mock.default_skills = dict(test_skill=skill)
    msm_mock.all_skills = [skill]
    msm_mock.local_skills = dict(test_skill=skill)

    return msm_mock


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
