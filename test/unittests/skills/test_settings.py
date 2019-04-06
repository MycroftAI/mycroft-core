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
import json
import unittest

from os import remove
from os.path import join, dirname

from mycroft.skills.settings import SkillSettings


class SkillSettingsTest(unittest.TestCase):
    def setUp(self):
        try:
            remove(join(dirname(__file__), 'settings', 'settings.json'))
        except OSError:
            pass

    def test_new(self):
        s = SkillSettings(join(dirname(__file__), 'settings'),
                          "test-skill-settings")
        self.assertEqual(len(s), 0)

    def test_add_value(self):
        s = SkillSettings(join(dirname(__file__), 'settings'),
                          "test-skill-settings")
        s['test_val'] = 1
        self.assertEqual(s['test_val'], 1)

    def test_store(self):
        s = SkillSettings(join(dirname(__file__), 'settings'),
                          "test-skill-settings")
        s.allow_overwrite = True
        s.load_skill_settings_from_file()
        s['bool'] = True
        s['int'] = 42
        s['float'] = 4.2
        s['string'] = 'Always carry a towel'
        s['list'] = ['batman', 2, True, 'superman']
        s.store()

        s2 = SkillSettings(join(dirname(__file__), 'settings'),
                           "test-skill-settings")
        s2.allow_overwrite = True
        s2.load_skill_settings_from_file()
        for key in s:
            self.assertEqual(s[key], s2[key])

    def test_update_list(self):
        s = SkillSettings(join(dirname(__file__), 'settings'),
                          "test-skill-settings")
        s.allow_overwrite = True
        s.load_skill_settings_from_file()
        s['l'] = ['a', 'b', 'c']
        s.store()
        s2 = SkillSettings(join(dirname(__file__), 'settings'),
                           "test-skill-settings")
        s2.allow_overwrite = True
        s2.load_skill_settings_from_file()
        self.assertEqual(s['l'], s2['l'])

        # Update list
        s2['l'].append('d')
        s2.store()
        s3 = SkillSettings(join(dirname(__file__), 'settings'),
                           "test-skill-settings")
        s3.allow_overwrite = True
        s3.load_skill_settings_from_file()
        self.assertEqual(s2['l'], s3['l'])

    def test_update_dict(self):
        s = SkillSettings(join(dirname(__file__), 'settings'),
                          "test-skill-settings")
        s.allow_overwrite = True
        s['d'] = {'a': 1, 'b': 2}
        s.store()
        s2 = SkillSettings(join(dirname(__file__), 'settings'),
                           "test-skill-settings")
        s2.allow_overwrite = True
        s2.load_skill_settings_from_file()
        self.assertEqual(s['d'], s2['d'])

        # Update dict
        s2['d']['c'] = 3
        s2.store()
        s3 = SkillSettings(join(dirname(__file__), 'settings'),
                           "test-skill-settings")
        s3.allow_overwrite = True
        s3.load_skill_settings_from_file()
        self.assertEqual(s2['d'], s3['d'])

    def test_no_change(self):
        s = SkillSettings(join(dirname(__file__), 'settings'),
                          "test-skill-settings")
        s.allow_overwrite = True
        s['d'] = {'a': 1, 'b': 2}
        s.store()

        s2 = SkillSettings(join(dirname(__file__), 'settings'),
                           "test-skill-settings")
        s2.allow_overwrite = True
        s2.load_skill_settings_from_file()
        self.assertTrue(len(s) == len(s2))

    def test_load_existing(self):
        directory = join(dirname(__file__), 'settings', 'settings.json')
        with open(directory, 'w') as f:
            json.dump({"test": "1"}, f)
        s = SkillSettings(join(dirname(__file__), 'settings'),
                          "test-skill-settings")
        s.allow_overwrite = True
        s.load_skill_settings_from_file()
        self.assertEqual(len(s), 1)


if __name__ == '__main__':
    unittest.main()
