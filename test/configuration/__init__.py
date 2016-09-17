import unittest

from os.path import dirname, join

from mycroft.configuration import ConfigurationLoader, ConfigurationManager, \
    DEFAULT_CONFIG, SYSTEM_CONFIG, USER_CONFIG, RemoteConfiguration

__author__ = 'jdorleans'


class AbstractConfigurationTest(unittest.TestCase):
    def setUp(self):
        self.config_path = join(dirname(__file__), 'mycroft.conf')

    @staticmethod
    def create_config(lang='en-us', module='mimic', voice="ap"):
        config = {
            'lang': lang,
            'tts': {
                'module': module,
                module: {'voice': voice}
            }
        }
        return config

    def assert_config(self, config, lang='en-us', module='mimic', voice="ap"):
        self.assertIsNotNone(config)
        lan = config.get('lang')
        self.assertIsNotNone(lan)
        self.assertEquals(lan, lang)
        tts = config.get('tts')
        self.assertIsNotNone(tts)
        mod = tts.get('module')
        self.assertEquals(mod, module)
        voi = tts.get(mod, {}).get("voice")
        self.assertEquals(voi, voice)


class ConfigurationLoaderTest(AbstractConfigurationTest):
    def test_init_config_with_defaults(self):
        self.assertEquals(ConfigurationLoader.init_config(), {})

    def test_init_config_with_new_config(self):
        config = {'a': 'b'}
        self.assertEquals(ConfigurationLoader.init_config(config), config)

    def test_init_locations_with_defaults(self):
        locations = [DEFAULT_CONFIG, SYSTEM_CONFIG, USER_CONFIG]
        self.assertEquals(ConfigurationLoader.init_locations(), locations)

    def test_init_locations_with_new_location(self):
        locations = [self.config_path]
        self.assertEquals(ConfigurationLoader.init_locations(locations),
                          locations)

    def test_validate_data(self):
        try:
            ConfigurationLoader.validate_data({}, [])
        except TypeError:
            self.fail()

    def test_validate_data_with_invalid_data(self):
        self.assertRaises(TypeError, ConfigurationLoader.validate_data)

    def test_load(self):
        self.assert_config(ConfigurationLoader.load())

    def test_load_with_override_custom(self):
        config = self.create_config('pt-br', 'espeak', 'f1')
        config = ConfigurationLoader.load(config)
        self.assert_config(config)

    def test_load_with_override_default(self):
        config = self.create_config()
        config = ConfigurationLoader.load(config, [self.config_path])
        self.assert_config(config, 'pt-br', 'espeak', 'f1')

    def test_load_with_extra_custom(self):
        my_config = {'key': 'value'}
        config = ConfigurationLoader.load(my_config)
        self.assert_config(config)

        value = config.get('key', None)
        self.assertIsNotNone(value)
        self.assertEquals(value, my_config.get('key'))

    def test_load_with_invalid_config_type(self):
        self.assertRaises(TypeError, ConfigurationLoader.load, 'invalid_type')

    def test_load_with_invalid_locations_type(self):
        self.assertRaises(TypeError, ConfigurationLoader.load,
                          None, self.config_path)

    def test_load_with_invalid_locations_path(self):
        locations = ['./invalid/mycroft.conf', './invalid_mycroft.conf']
        config = ConfigurationLoader.load(None, locations, False)
        self.assertEquals(config, {})


class RemoteConfigurationTest(AbstractConfigurationTest):
    def test_validate_config(self):
        try:
            RemoteConfiguration.validate_config(self.create_config())
        except TypeError:
            self.fail()

    def test_validate_config_with_invalid_config(self):
        self.assertRaises(TypeError, RemoteConfiguration.validate_config)

    def test_load_without_remote_config(self):
        config = self.create_config()
        self.assertEquals(RemoteConfiguration.load(config), config)


class ConfigurationManagerTest(AbstractConfigurationTest):
    def test_load_defaults(self):
        ConfigurationManager.load_defaults()
        self.assert_config(ConfigurationManager.load_defaults())

    def test_load_local(self):
        ConfigurationManager.load_defaults()
        self.assert_config(ConfigurationManager.load_local())

    def test_load_local_with_locations(self):
        ConfigurationManager.load_defaults()
        config = ConfigurationManager.load_local([self.config_path])
        self.assert_config(config, 'pt-br', 'espeak', 'f1')

    def test_load_remote(self):
        ConfigurationManager.load_defaults()
        self.assert_config(ConfigurationManager.load_remote())

    def test_get(self):
        ConfigurationManager.load_defaults()
        self.assert_config(ConfigurationManager.get())

    def test_load_get_with_locations(self):
        ConfigurationManager.load_defaults()
        config = ConfigurationManager.get([self.config_path])
        self.assert_config(config, 'pt-br', 'espeak', 'f1')
