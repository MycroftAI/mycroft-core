# Copyright 2021 Mycroft AI Inc.
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
"""TTS cache maintenance.

There are two types of cache available to a TTS engine.  Both are comprised of
audio and phoneme files.  TTS engines can use the cache to improve performance
by not performing inference on sentences in the cache.

The first type of cache is a persistent cache.  The cache is considered
persistent because the files are stored in a location that is not cleared on
reboot.  TTS inference on these sentences should only need to occur once.  The
persistent cache contains commonly spoken sentences.

The second cache type a temporary cache stored in the /tmp directory,
which is cleared when a device is rebooted.  Sentences are added to this cache
on the fly every time a TTS engine returns audio for a sentence that is not
already cached.
"""
import base64
import hashlib
import re
from collections import defaultdict
from pathlib import Path
from typing import List, Optional, Set, Tuple
from urllib import parse

import requests

from mycroft.util.file_utils import (
    ensure_directory_exists, get_cache_directory
)
from mycroft.util.log import LOG


def _get_mimic2_audio(sentence: str, url: str) -> Tuple[bytes, str]:
    """Use the Mimic2 API to retrieve the audio for a sentence.

    Arguments:
        sentence: The sentence to be cached
    """
    LOG.debug("Retrieving Mimic2 audio for sentence \"{}\'".format(sentence))
    mimic2_url = url + parse.quote(sentence) + '&visimes=True'
    response = requests.get(mimic2_url)
    response_data = response.json()
    audio = base64.b64decode(response_data["audio_base64"])
    phonemes = response_data["visimes"]

    return audio, phonemes


def hash_sentence(sentence):
    encoded_sentence = sentence.encode("utf-8", "ignore")
    sentence_hash = hashlib.md5(encoded_sentence).hexdigest()

    return sentence_hash


class TextToSpeechCache:
    def __init__(self, tts_config, tts_name, audio_file_type):
        self.config = tts_config
        self.tts_name = tts_name
        self.persistent_cache_dir = Path(tts_config["preloaded_cache"])
        self.temporary_cache_dir = Path(
            get_cache_directory("tts/" + tts_name)
        )
        self.audio_file_type = audio_file_type
        self.resource_dir = Path(__file__).parent.parent.joinpath("res")
        self.cached_sentences = dict()
        ensure_directory_exists(
            str(self.persistent_cache_dir), permissions=0o755
        )
        ensure_directory_exists(
            str(self.temporary_cache_dir), permissions=0o755
        )

    def load_persistent_cache(self):
        """Load the contents of dialog files to the persistent cache directory.

        Parse the dialog files in the resource directory into sentences.  Then
        add the audio for each sentence to the cache directory.

        NOTE: There may be files pre-loaded in the persistent cache directory
        prior to run time, such as pre-recorded audio files.  This will add
        files that do not already exist.

        ANOTHER NOTE:  Mimic2 is the only TTS engine that supports this.  This
        logic will need to change if another TTS engine implements it.
        """
        if self.tts_name == "Mimic2":
            LOG.info("Adding dialog resources to persistent TTS cache...")
            preloaded_files = self._find_preloaded_files()
            self._add_preloaded_files(preloaded_files)
            dialogs = self._collect_dialogs()
            sentences = self._parse_dialogs(dialogs)
            for sentence in sentences:
                self._load_sentence(sentence)
            LOG.info("Persistent TTS cache files added successfully.")

    def _find_preloaded_files(self):
        preloaded_files = defaultdict(list)
        for preloaded_file in self.persistent_cache_dir.iterdir():
            if preloaded_file.name.endswith(self.audio_file_type):
                sentence_hash = preloaded_file.name.strip(
                    "." + self.audio_file_type
                )
                preloaded_files[sentence_hash].append("audio")
            else:
                sentence_hash = preloaded_file.name.strip(
                    "." + self.audio_file_type
                )
                preloaded_files[sentence_hash].append("phoneme")

        return preloaded_files

    def _add_preloaded_files(self, preloaded_files):
        for sentence_hash, file_types in preloaded_files.items():
            if "audio" in file_types:
                audio_file = self.define_audio_file(sentence_hash)
                phoneme_file = None
                if "phoneme" in file_types:
                    phoneme_file = self.define_phoneme_file(sentence_hash)
                self.cached_sentences[sentence_hash] = audio_file, phoneme_file

    def _collect_dialogs(self) -> List:
        """Build a set of unique sentences from the dialog files.

        The sentences will be parsed from *.dialog files present in
        mycroft/res/text/en-us.
        """
        dialogs = []
        dialog_directory = Path(self.resource_dir, "text", "en-us")
        for dialog_file_path in dialog_directory.glob("*.dialog"):
            with open(dialog_file_path) as dialog_file:
                for dialog in dialog_file.readlines():
                    dialogs.append(dialog.strip())

        return dialogs

    @staticmethod
    def _parse_dialogs(dialogs: List[str]) -> Set[str]:
        """Split each dialog in the resources directory into sentences.

        Do not consider sentences with special characters other than punctuation
            example : <<< LOADING <<<

        Arguments:
            dialogs: a list of the records in the dialog resource files
        """
        sentences = set()
        dialog_split_regex = r"(?<=\.|\;|\?)\s"
        special_characters_regex = re.compile(r"[@#$%^*()<>/|}{~:]")
        for dialog in dialogs:
            dialog_sentences = re.split(dialog_split_regex, dialog)
            for sentence in dialog_sentences:
                match = special_characters_regex.search(sentence)
                if match is None:
                    sentences.add(sentence)

        return sentences

    def _load_sentence(self, sentence: str):
        """Build audio and phoneme files for each sentence to be cached.

        Perform TTS inference on sentences parsed from dialog files.  Store
        the results in the persistent cache directory.

        ASSUMPTION: The only TTS that supports persistent cache right now is
        Mimic2.  This method assumes a call to the Mimic2 API.  If other TTS
        engines want to take advantage of the persistent cache, this logic
        will need to be more dynamic.
        """
        sentence_hash = hash_sentence(sentence)
        if sentence_hash not in self.cached_sentences:
            LOG.info("Adding \"{}\" to cache".format(sentence))
            try:
                mimic2_url = self.config["mimic2"]["url"]
                audio, phonemes = _get_mimic2_audio(sentence, mimic2_url)
            except Exception:
                log_msg = "Failed to get audio for sentence \"{}\""
                LOG.exception(log_msg.format(sentence))
            else:
                self.add_to_cache(sentence_hash, audio, phonemes)

    def add_to_cache(self, sentence_hash: str, audio: bytes, phonemes: str):
        audio_file = self.define_audio_file(sentence_hash)
        audio_file.save(audio)
        if phonemes is None:
            phoneme_file = None
        else:
            phoneme_file = self.define_phoneme_file(sentence_hash)
            phoneme_file.save(phonemes)
        self.cached_sentences[sentence_hash] = audio_file, phoneme_file

    def clear(self):
        """Remove all files from the temporary cache."""
        for cache_file_path in self.temporary_cache_dir.iterdir():
            if cache_file_path.is_dir():
                for sub_path in cache_file_path.iterdir():
                    if sub_path.is_file():
                        sub_path.unlink()
            elif cache_file_path.is_file():
                cache_file_path.unlink()

    def define_audio_file(self, sentence_hash):
        audio_file = AudioFile(
            self.persistent_cache_dir, sentence_hash, self.audio_file_type
        )
        return audio_file

    def define_phoneme_file(self, sentence_hash):
        phoneme_file = PhonemeFile(
            self.persistent_cache_dir, sentence_hash
        )
        return phoneme_file


class AudioFile:
    def __init__(self, cache_dir: Path, sentence_hash: str, file_type: str):
        self.name = f"{sentence_hash}.{file_type}"
        self.path = cache_dir.joinpath(self.name)

    def save(self, audio: bytes):
        """Write a TTS cache file containing the audio to be spoken.

        Arguments:
            audio: TTS inference of a sentence
        """
        try:
            with open(self.path, "wb") as audio_file:
                audio_file.write(audio)
        except Exception:
            LOG.exception("Failed to write {} to cache".format(self.name))


class PhonemeFile:
    def __init__(self, cache_dir: Path, sentence_hash: str):
        self.name = f"{sentence_hash}.pho"
        self.path = cache_dir.joinpath(self.name)

    def load(self) -> str:
        """Load phonemes from cache file."""
        phonemes = None
        if self.path.exists():
            try:
                with open(self.path) as phoneme_file:
                    phonemes = phoneme_file.read().strip()
            except Exception:
                LOG.exception("Failed to read phoneme from cache")

        return phonemes

    def save(self, phonemes: str):
        """Write a TTS cache file containing the phoneme to be displayed.

        Arguments:
            phonemes: instructions for how to make the mouth on a device move
        """
        try:
            with open(self.path, "w") as phoneme_file:
                phoneme_file.write(phonemes)
        except Exception:
            LOG.exception("Failed to write {} to cache".format(self.name))
