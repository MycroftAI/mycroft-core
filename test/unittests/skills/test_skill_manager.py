import unittest
import mock
import copy
import tempfile
from os.path import exists, join
from shutil import rmtree
from test.util import base_config

from mycroft.configuration import Configuration
from mycroft.skills.skill_manager import SkillManager

BASE_CONF = base_config()
BASE_CONF['skills'] = {
    'msm': {
        'directory': 'skills',
        'versioned': True,
        'repo': {
            'cache': '.skills-repo',
            'url': 'https://github.com/MycroftAI/mycroft-skills',
            'branch': '19.02'
        }
    },
    'update_interval': 3600,
    'auto_update': False,
    'blacklisted_skills': [],
    'priority_skills': ["mycroft-pairing"]
}


class MockEmitter(object):
    def __init__(self):
        self.reset()

    def emit(self, message):
        self.types.append(message.type)
        self.results.append(message.data)

    def get_types(self):
        return self.types

    def get_results(self):
        return self.results

    def on(self, event, f):
        pass

    def reset(self):
        self.types = []
        self.results = []


class MycroftSkillTest(unittest.TestCase):
    emitter = MockEmitter()

    def setUp(self):
        self.emitter.reset()
        self.temp_dir = tempfile.mkdtemp()

    def test_create_manager(self):
        """ Verify that the skill manager and msm loads as expected and
            that the skills dir is created as needed.
        """
        conf = copy.deepcopy(BASE_CONF)
        conf['data_dir'] = self.temp_dir
        with mock.patch.dict(Configuration._Configuration__config,
                             BASE_CONF):
            SkillManager(self.emitter)
            self.assertTrue(exists(join(BASE_CONF['data_dir'], 'skills')))

    def tearDown(self):
        rmtree(self.temp_dir)
