import mock
from unittest import TestCase
import mycroft.configuration


class TestConfiguration(TestCase):
    def setUp(self):
        """
            Clear cached configuration
        """
        super(TestConfiguration, self).setUp()
        mycroft.configuration.Configuration.load_config_stack([{}], True)

    def test_get(self):
        d1 = {'a': 1, 'b': {'c': 1, 'd': 2}}
        d2 = {'b': {'d': 'changed'}}
        d = mycroft.configuration.Configuration.get([d1, d2])
        self.assertEquals(d['a'], d1['a'])
        self.assertEquals(d['b']['d'], d2['b']['d'])
        self.assertEquals(d['b']['c'], d1['b']['c'])

    @mock.patch('mycroft.api.DeviceApi')
    def test_remote(self, mock_api):
        remote_conf = {'TestConfig': True, 'uuid': 1234}
        remote_location = {'city': {'name': 'Stockholm'}}
        dev_api = mock.MagicMock()
        dev_api.get_settings.return_value = remote_conf
        dev_api.get_location.return_value = remote_location
        mock_api.return_value = dev_api

        rc = mycroft.configuration.RemoteConf()
        self.assertTrue(rc['test_config'])
        self.assertEquals(rc['location']['city']['name'], 'Stockholm')

    @mock.patch('json.dump')
    @mock.patch('mycroft.configuration.config.exists')
    @mock.patch('mycroft.configuration.config.isfile')
    @mock.patch('mycroft.configuration.config.load_commented_json')
    def test_local(self, mock_json_loader, mock_isfile, mock_exists,
                   mock_json_dump):
        local_conf = {'answer': 42, 'falling_objects': ['flower pot', 'whale']}
        mock_exists.return_value = True
        mock_isfile.return_value = True
        mock_json_loader.return_value = local_conf
        lc = mycroft.configuration.LocalConf('test')
        self.assertEquals(lc, local_conf)

        # Test merge method
        merge_conf = {'falling_objects': None, 'has_towel': True}
        lc.merge(merge_conf)
        self.assertEquals(lc['falling_objects'], None)
        self.assertEquals(lc['has_towel'], True)

        # test store
        lc.store('test_conf.json')
        self.assertEquals(mock_json_dump.call_args[0][0], lc)
        # exists but is not file
        mock_isfile.return_value = False
        lc = mycroft.configuration.LocalConf('test')
        self.assertEquals(lc, {})

        # does not exist
        mock_exists.return_value = False
        lc = mycroft.configuration.LocalConf('test')
        self.assertEquals(lc, {})

    @mock.patch('mycroft.configuration.config.RemoteConf')
    @mock.patch('mycroft.configuration.config.LocalConf')
    def test_update(self, mock_remote, mock_local):
        mock_remote.return_value = {}
        mock_local.return_value = {'a': 1}
        c = mycroft.configuration.Configuration.get()
        self.assertEquals(c, {'a': 1})

        mock_local.return_value = {'a': 2}
        mycroft.configuration.Configuration.updated('message')
        self.assertEquals(c, {'a': 2})

    def tearDown(self):
        mycroft.configuration.Configuration.load_config_stack([{}], True)
