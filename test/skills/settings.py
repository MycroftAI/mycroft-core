from mycroft.skills.settings import SkillSettings

from os.path import join, dirname, abspath
from os import remove
import unittest


class SkillSettingsTest(unittest.TestCase):
    def setUp(self):
        try:
            remove(join(dirname(__file__), 'settings', 'store.json'))
        except OSError:
            pass

    def test_new(self):
        s = SkillSettings(join(dirname(__file__), 'settings.json'))
        self.assertEqual(len(s), 0)

    def test_add_value(self):
        s = SkillSettings(join(dirname(__file__), 'settings.json'))
        s['test_val'] = 1

    def test_load_existing(self):
        s = SkillSettings(join(dirname(__file__), 'settings', 'existing.json'))
        self.assertEqual(len(s), 4)

    def test_store(self):
        s = SkillSettings(join(dirname(__file__), 'settings', 'store.json'))
        s['bool'] = True
        s['int'] = 42
        s['float'] = 4.2
        s['string'] = 'Always carry a towel'
        s['list'] = ['batman', 2, True, 'superman']
        s.store()

        s2 = SkillSettings(join(dirname(__file__), 'settings', 'store.json'))
        for key in s:
            self.assertEqual(s[key], s2[key])
