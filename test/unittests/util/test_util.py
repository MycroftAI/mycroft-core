from os.path import (abspath, dirname, expanduser, join, normpath, isdir,
                     exists)
import shutil
import tempfile
from unittest import TestCase, mock

from mycroft import MYCROFT_ROOT_PATH
from mycroft.util import (resolve_resource_file, curate_cache,
                          get_cache_directory, play_ogg, play_mp3, play_wav,
                          play_audio_file,
                          camel_case_split, get_http, remove_last_slash)

test_config = {
    'data_dir': join(dirname(__file__), 'datadir'),
    'cache_dir': tempfile.gettempdir(),
    'play_wav_cmdline': 'mock_wav %1',
    'play_mp3_cmdline': 'mock_mp3 %1',
    'play_ogg_cmdline': 'mock_ogg %1'
}


class Anything:
    """Class matching any object.

    Useful for assert_called_with arguments.
    """
    def __eq__(self, other):
        return True


@mock.patch('mycroft.configuration.Configuration')
class TestResolveResource(TestCase):
    def test_absolute_path(self, mock_conf):
        mock_conf.get.return_value = test_config
        test_path = abspath(__file__)

        self.assertEqual(resolve_resource_file(test_path), test_path)

    @mock.patch('os.path.isfile')
    def test_dot_mycroft(self, mock_isfile, mock_conf):
        mock_conf.get.return_value = test_config

        def files_in_dotmycroft_exists(path):
            return '.mycroft/' in path

        mock_isfile.side_effect = files_in_dotmycroft_exists
        self.assertEqual(resolve_resource_file('1984.txt'),
                         expanduser('~/.mycroft/1984.txt'))

    @mock.patch('os.path.isfile')
    def test_data_dir(self, mock_isfile, mock_conf):
        """Check for file in the "configured data dir"/res/"""
        mock_conf.get.return_value = test_config

        def files_in_mycroft_datadir_exists(path):
            return 'datadir' in path

        mock_isfile.side_effect = files_in_mycroft_datadir_exists
        self.assertEqual(resolve_resource_file('1984.txt'),
                         join(test_config['data_dir'], 'res', '1984.txt'))

    def test_source_package(self, mock_conf):
        """Check file shipped in the mycroft res folder."""
        mock_conf.get.return_value = test_config
        expected_path = join(MYCROFT_ROOT_PATH, 'mycroft', 'res',
                             'text', 'en-us', 'and.word')
        res_path = resolve_resource_file('text/en-us/and.word')

        self.assertEqual(normpath(res_path), normpath(expected_path))

    def test_missing_file(self, mock_conf):
        """Assert that the function returns None when file is not foumd."""
        mock_conf.get.return_value = test_config
        self.assertTrue(resolve_resource_file('1984.txt') is None)


def create_cache_files(cache_dir):
    """Create a couple of files in the cache directory."""
    huxley_path = join(cache_dir, 'huxley.txt')
    aldous_path = join(cache_dir, 'alduos.txt')
    f = open(huxley_path, 'w+')
    f.close()
    f = open(aldous_path, 'w+')
    f.close()
    return huxley_path, aldous_path


@mock.patch('mycroft.configuration.Configuration')
class TestCache(TestCase):
    def tearDownClass():
        shutil.rmtree(test_config['cache_dir'], ignore_errors=True)

    def test_get_cache_directory(self, mock_conf):
        mock_conf.get.return_value = test_config
        expected_path = join(test_config['cache_dir'], 'mycroft', 'cache')
        self.assertEqual(get_cache_directory(), expected_path)
        self.assertTrue(isdir(expected_path))

    def test_get_cache_directory_with_domain(self, mock_conf):
        mock_conf.get.return_value = test_config
        expected_path = join(test_config['cache_dir'], 'mycroft',
                             'cache', 'whales')
        self.assertEqual(get_cache_directory('whales'), expected_path)
        self.assertTrue(isdir(expected_path))

    @mock.patch('mycroft.util.file_utils.psutil')
    def test_curate_cache(self, mock_psutil, mock_conf):
        """Test removal of cache files when disk space is running low."""
        mock_conf.get.return_value = test_config
        space = mock.Mock(name='diskspace')
        mock_psutil.disk_usage.return_value = space

        cache_dir = get_cache_directory('braveNewWorld')
        huxley_path, aldous_path = create_cache_files(cache_dir)
        # Create files in the cache directory

        # Test plenty of space free
        space.percent = 5.0
        space.free = 2 * 1024 * 1024 * 1024  # 2GB
        space.total = 20 * 1024 * 1024 * 1024  # 20GB
        curate_cache(cache_dir)
        self.assertTrue(exists(aldous_path))
        self.assertTrue(exists(huxley_path))

        # Free Percentage low but not free space
        space.percent = 96.0
        space.free = 2 * 1024 * 1024 * 1024  # 2GB
        curate_cache(cache_dir)
        self.assertTrue(exists(aldous_path))
        self.assertTrue(exists(huxley_path))

        # Free space low, but not percentage
        space.percent = 95.0
        space.free = 2 * 1024 * 1024  # 2MB
        curate_cache(cache_dir)
        self.assertTrue(exists(aldous_path))
        self.assertTrue(exists(huxley_path))

        # Free space and percentage low
        space.percent = 96.0
        space.free = 2 * 1024 * 1024  # 2MB
        curate_cache(cache_dir)
        self.assertFalse(exists(aldous_path))
        self.assertFalse(exists(huxley_path))


@mock.patch('mycroft.configuration.Configuration')
@mock.patch('mycroft.util.audio_utils.subprocess')
class TestPlaySounds(TestCase):
    def test_play_ogg(self, mock_subprocess, mock_conf):
        mock_conf.get.return_value = test_config
        play_ogg('insult.ogg')
        mock_subprocess.Popen.assert_called_once_with(['mock_ogg',
                                                       'insult.ogg'],
                                                      env=Anything())

    def test_play_mp3(self, mock_subprocess, mock_conf):
        mock_conf.get.return_value = test_config
        play_mp3('praise.mp3')
        mock_subprocess.Popen.assert_called_once_with(['mock_mp3',
                                                       'praise.mp3'],
                                                      env=Anything())

    def test_play_wav(self, mock_subprocess, mock_conf):
        mock_conf.get.return_value = test_config
        play_wav('indifference.wav')
        mock_subprocess.Popen.assert_called_once_with(['mock_wav',
                                                       'indifference.wav'],
                                                      env=Anything())

    def test_play_audio_file(self, mock_subprocess, mock_conf):
        mock_conf.get.return_value = test_config
        play_audio_file('indifference.wav')
        mock_subprocess.Popen.assert_called_once_with(['mock_wav',
                                                       'indifference.wav'],
                                                      env=Anything())
        mock_subprocess.Popen.reset_mock()

        play_audio_file('praise.mp3')
        mock_subprocess.Popen.assert_called_once_with(['mock_mp3',
                                                       'praise.mp3'],
                                                      env=Anything())
        mock_subprocess.Popen.reset_mock()
        mock_conf.get.return_value = test_config
        play_audio_file('insult.ogg')
        mock_subprocess.Popen.assert_called_once_with(['mock_ogg',
                                                       'insult.ogg'],
                                                      env=Anything())


class TestStringFunctions(TestCase):
    def test_camel_case_split(self):
        """Check that camel case string is split properly."""
        self.assertEqual(camel_case_split('MyCoolSkill'), 'My Cool Skill')
        self.assertEqual(camel_case_split('MyCOOLSkill'), 'My COOL Skill')

    def test_get_http(self):
        """Check that https-url is correctly transformed to a http-url."""
        self.assertEqual(get_http('https://github.com/'), 'http://github.com/')
        self.assertEqual(get_http('http://github.com/'), 'http://github.com/')
        self.assertEqual(get_http('https://github.com/https'),
                         'http://github.com/https')
        self.assertEqual(get_http('http://https.com/'), 'http://https.com/')

    def test_remove_last_slash(self):
        """Check that the last slash in an url is correctly removed."""
        self.assertEqual(remove_last_slash('https://github.com/'),
                         'https://github.com')
        self.assertEqual(remove_last_slash('https://github.com/hello'),
                         'https://github.com/hello')
        self.assertEqual(remove_last_slash('https://github.com/hello/'),
                         'https://github.com/hello')
