"""Unit tests for the functionality in the TTS cache module."""
from pathlib import Path
from tempfile import mkdtemp
from unittest import TestCase
from unittest.mock import Mock, MagicMock, patch

from mycroft.tts.cache import hash_sentence, TextToSpeechCache


def _mock_mimic2_api():
    response = MagicMock()
    response.json = MagicMock()
    response.json.return_value = dict(audio_base64=b'', visimes=None)

    return response


class TestCache(TestCase):
    def setUp(self) -> None:
        self.cache_dir = Path(mkdtemp())

    def tearDown(self) -> None:
        for file_path in self.cache_dir.iterdir():
            file_path.unlink()
        self.cache_dir.rmdir()

    def test_sentence_hash(self):
        sentence = "This is a test sentence."
        sentence_hash = hash_sentence(sentence)
        self.assertEqual("4d6a0c4cf3f07eadd5ba147c67c6896f", sentence_hash)

    @patch("mycroft.tts.cache.requests.get")
    def test_persistent_cache(self, requests_mock):
        preloaded_file_path = self._write_preloaded_file()
        before_modified_time = preloaded_file_path.stat().st_mtime
        requests_mock.return_value = _mock_mimic2_api()
        tts_config = dict(preloaded_cache=self.cache_dir, url="testurl")
        tts_cache = self._load_persistent_cache(tts_config)
        actual_file_names = [path.name for path in self.cache_dir.iterdir()]

        self.assertEqual(3, len(actual_file_names))
        expected_file_names = [
            "92ee7866d8154bb2cbf6fb49504e49fc.wav",
            "70a73739cdebeffed0a6c692908c4c1f.wav",
            "ed110791065a474b0fa00098450da19b.wav"
        ]
        for file_name in expected_file_names:
            self.assertIn(file_name, actual_file_names)
            sentence_hash = file_name.split(".")[0]
            self.assertIn(sentence_hash, tts_cache.cached_sentences.keys())

        # Any pre-loaded cache files should not be overlaid
        after_modified_time = preloaded_file_path.stat().st_mtime
        self.assertEqual(before_modified_time, after_modified_time)

    def test_no_persistent_cache(self):
        tts_config = dict(url="testurl")
        tts_cache = self._load_persistent_cache(tts_config)
        actual_file_names = [path.name for path in self.cache_dir.iterdir()]

        self.assertEqual(0, len(actual_file_names))
        self.assertEqual(0, len(tts_cache.cached_sentences))

    def _write_preloaded_file(self):
        preloaded_file_name = "92ee7866d8154bb2cbf6fb49504e49fc.wav"
        preloaded_file_path = self.cache_dir.joinpath(preloaded_file_name)
        with open(preloaded_file_path, 'w') as test_file:
            test_file.write("This is sentence one.")

        return preloaded_file_path

    def _load_persistent_cache(self, tts_config):
        test_resource_directory = Path(__file__).parent.parent.joinpath("res")
        tts_cache = TextToSpeechCache(
            tts_config=tts_config,
            tts_name="Test",
            audio_file_type="wav"
        )
        tts_cache.resource_dir = test_resource_directory
        tts_cache.load_persistent_cache()

        return tts_cache

    def test_clear_cache(self):
        with open(self.cache_dir.joinpath('test.txt'), 'w') as test_file:
            test_file.write("testing testing")

        tts_cache = TextToSpeechCache(
            tts_config=dict(preloaded_cache=self.cache_dir),
            tts_name="Test",
            audio_file_type="wav"
        )
        tts_cache.temporary_cache_dir = self.cache_dir
        tts_cache.clear()
        cache_contents = [path for path in self.cache_dir.iterdir()]
        self.assertListEqual([], cache_contents)

    @patch('mycroft.tts.cache.curate_cache')
    def test_curate_cache(self, curate_mock):
        tts_cache = TextToSpeechCache(
            tts_config=dict(preloaded_cache=self.cache_dir),
            tts_name="Test",
            audio_file_type="wav"
        )
        # Setup content of sentence cache
        files = {'kermit': tts_cache.define_audio_file('kermit'),
                 'fozzie': tts_cache.define_audio_file('fozzie'),
                 'gobo': tts_cache.define_audio_file('gobo')}
        for sentence_hash, audio_file in files.items():
            tts_cache.cached_sentences[sentence_hash] = (audio_file, None)

        # Set curate_cache() to report that paths to kermit and gobo
        # was removed
        curate_mock.return_value = [files['kermit'].path,
                                    files['gobo'].path]
        tts_cache.curate()
        curate_mock.assert_called_with(tts_cache.temporary_cache_dir,
                                       min_free_percent=100)

        # Verify that the "hashes" kermit and gobo was removed from the
        # dict of hashes.
        self.assertEqual(tts_cache.cached_sentences,
                         {'fozzie': (files['fozzie'], None)})


class MockFile(Mock):
    def __init__(self, exists, *args, **kwargs):
        super().__init__(args, kwargs)
        self._exists = exists

    def exists(self):
        return self._exists


class TestCacheContains(TestCase):
    """Verify the `"X" in tts_cache` functionality."""
    def setUp(self):
        self.cache_dir = Path(mkdtemp())
        self.tts_cache = TextToSpeechCache(
            tts_config=dict(preloaded_cache=self.cache_dir),
            tts_name="Test",
            audio_file_type="wav"
        )
        files = {
            'kermit': (MockFile(exists=True), MockFile(exists=True)),
            'fozzie': (MockFile(exists=True), None),
            'gobo': (MockFile(exists=False), None),
            'piggy': (MockFile(exists=True), MockFile(exists=False))
        }
        for sentence_hash, (audio_file, phoneme_file) in files.items():
            self.tts_cache.cached_sentences[sentence_hash] = (
                audio_file, phoneme_file
            )

    def tearDown(self):
        for file_path in self.cache_dir.iterdir():
            file_path.unlink()
        self.cache_dir.rmdir()

    def test_hash_not_listed(self):
        self.assertFalse('animal' in self.tts_cache)

    def test_hash_exists_and_files_ok(self):
        self.assertTrue('kermit' in self.tts_cache)

    def test_only_audio_hash_exists_and_files_ok(self):
        self.assertTrue('fozzie' in self.tts_cache)

    def test_hash_exists_and_files_bad(self):
        self.assertFalse('piggy' in self.tts_cache)
        self.assertFalse('gobo' in self.tts_cache)
