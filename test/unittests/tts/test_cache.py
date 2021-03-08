"""Unit tests for the functionality in the TTS cache module."""
from pathlib import Path
from tempfile import mkdtemp
from unittest import TestCase
from unittest.mock import MagicMock, patch

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
        tts_cache = self._load_persistent_cache()
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

    def _write_preloaded_file(self):
        preloaded_file_name = "92ee7866d8154bb2cbf6fb49504e49fc.wav"
        preloaded_file_path = self.cache_dir.joinpath(preloaded_file_name)
        with open(preloaded_file_path, 'w') as test_file:
            test_file.write("This is sentence one.")

        return preloaded_file_path

    def _load_persistent_cache(self):
        test_resource_directory = Path(__file__).parent.parent.joinpath("res")
        tts_cache = TextToSpeechCache(
            tts_config=dict(preloaded_cache=self.cache_dir),
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
