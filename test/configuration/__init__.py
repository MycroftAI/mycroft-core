import unittest

from mycroft.configuration import ConfigurationLoader

__author__ = 'jdorleans'


class ConfigurationLoaderTest(unittest.TestCase):
    @staticmethod
    def create_config(lang='en-us', module='mimic'):
        config = {
            'core': {'lang': lang},
            'tts': {'module': module}
        }
        return config

    def assert_config(self, config, lang='en-us', module='mimic'):
        self.assertIsNotNone(config)
        core = config.get('core', None)
        self.assertIsNotNone(core)
        lan = core.get('lang', None)
        self.assertIsNotNone(lan)
        self.assertEquals(lan, lang)
        tts = config.get('tts', None)
        self.assertIsNotNone(tts)
        mod = tts.get('module', None)
        self.assertEquals(mod, module)

    def test_load_default(self):
        config = ConfigurationLoader.load()
        self.assert_config(config)

    def test_load_override_custom(self):
        config = self.create_config('pt-br', 'espeak')
        config = ConfigurationLoader.load(config)
        self.assert_config(config)

    def test_load_override_default(self):
        config = self.create_config()
        config = ConfigurationLoader.load(config, ['./mycroft.ini'])
        self.assert_config(config, 'pt-br', 'espeak')

    def test_load_do_not_override(self):
        my_config = {'key': 'value'}
        config = ConfigurationLoader.load(my_config)
        self.assert_config(config)

        value = config.get('key', None)
        self.assertIsNotNone(value)
        self.assertEquals(value, my_config.get('key'))

    def test_load_invalid_config_type(self):
        invalid_type = 'invalid_type'
        config = ConfigurationLoader.load(invalid_type)
        self.assertEquals(config, invalid_type)

    def test_load_invalid_locations_type(self):
        config = ConfigurationLoader.load(None, './mycroft.ini')
        self.assertEquals(config, {})

    def test_load_invalid_locations_path(self):
        locations = ['./invalid/mycroft.ini', './invalid_mycroft.ini']
        config = ConfigurationLoader.load(None, locations)
        self.assertEquals(config, {})


class ConfigurationManagerTest(unittest.TestCase):
    @staticmethod
    def create_config(lang='en-us', module='mimic'):
        config = {
            'core': {'lang': lang},
            'tts': {'module': module}
        }
        return config

    def assert_config(self, config, lang='en-us', module='mimic'):
        self.assertIsNotNone(config)
        core = config.get('core', None)
        self.assertIsNotNone(core)
        lan = core.get('lang', None)
        self.assertIsNotNone(lan)
        self.assertEquals(lan, lang)
        tts = config.get('tts', None)
        self.assertIsNotNone(tts)
        mod = tts.get('module', None)
        self.assertEquals(mod, module)

    def test_load_default(self):
        config = ConfigurationLoader.load()
        self.assert_config(config)

    def test_load_override_custom(self):
        config = self.create_config('pt-br', 'espeak')
        config = ConfigurationLoader.load(config)
        self.assert_config(config)

    def test_load_override_default(self):
        config = self.create_config()
        config = ConfigurationLoader.load(config, ['./mycroft.ini'])
        self.assert_config(config, 'pt-br', 'espeak')

    def test_load_do_not_override(self):
        my_config = {'key': 'value'}
        config = ConfigurationLoader.load(my_config)
        self.assert_config(config)

        value = config.get('key', None)
        self.assertIsNotNone(value)
        self.assertEquals(value, my_config.get('key'))

    def test_load_invalid_config_type(self):
        invalid_type = 'invalid_type'
        config = ConfigurationLoader.load(invalid_type)
        self.assertEquals(config, invalid_type)

    def test_load_invalid_locations_type(self):
        config = ConfigurationLoader.load(None, './mycroft.ini')
        self.assertEquals(config, {})

    def test_load_invalid_locations_path(self):
        locations = ['./invalid/mycroft.ini', './invalid_mycroft.ini']
        config = ConfigurationLoader.load(None, locations)
        self.assertEquals(config, {})
