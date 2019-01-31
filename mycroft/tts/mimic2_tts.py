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

from mycroft.tts import TTS, TTSValidator
from mycroft.tts.remote_tts import RemoteTTSTimeoutException
from mycroft.util.log import LOG
from mycroft.util.format import pronounce_number
from mycroft.util import play_wav, get_cache_directory, create_signal
from requests_futures.sessions import FuturesSession
from requests.exceptions import (
    ReadTimeout, ConnectionError, ConnectTimeout, HTTPError
)
from urllib import parse
from .mimic_tts import VISIMES
import math
import base64
import os
import hashlib
import re
import json


max_sentence_size = 170


def break_chunks(l, n):
    """Yield successive n-sized chunks from l."""
    for i in range(0, len(l), n):
        yield " ".join(l[i:i + n])


def split_by_chunk_size(text, chunk_size):
    """split text into word chunks by chunk_size size

    Args:
        text (str): text to split
        chunk_size (int): chunk size

    Returns:
        list: list of text chunks
    """
    text_list = text.split()

    if len(text_list) <= chunk_size:
        return [text]

    if chunk_size < len(text_list) < (chunk_size * 2):
        return list(break_chunks(
            text_list,
            int(math.ceil(len(text_list) / 2))
        ))
    elif (chunk_size * 2) < len(text_list) < (chunk_size * 3):
        return list(break_chunks(
            text_list,
            int(math.ceil(len(text_list) / 3))
        ))
    elif (chunk_size * 3) < len(text_list) < (chunk_size * 4):
        return list(break_chunks(
            text_list,
            int(math.ceil(len(text_list) / 4))
        ))
    else:
        return list(break_chunks(
            text_list,
            int(math.ceil(len(text_list) / 5))
        ))


def split_by_punctuation(text, puncs):
    """splits text by various punctionations
    e.g. hello, world => [hello, world]

    Args:
        text (str): text to split
        puncs (list): list of punctuations used to split text

    Returns:
        list: list with split text
    """
    splits = text.split()
    split_by_punc = False
    for punc in puncs:
        if punc in text:
            splits = text.split(punc)
            split_by_punc = True
            break
    if split_by_punc:
        return splits
    else:
        return [text]


def add_punctuation(text):
    """add punctuation at the end of each chunk. Mimic2
    expects some form of punctuations
    """
    punctuations = ['.', '?', '!']
    if len(text) < 1:
        return text
    if text[-1] not in punctuations:
        text += '.'
    return text


def sentence_chunker(text, chunk_size, split_by_punc=True):
    """split sentences into chunks. if split_by_punc is True,
        sentences will be split into chunks by punctuations first
        then those chunks will be split by chunk size

    Args:
        text (str): text to split
        chunk_size (int): size of each chunk
        split_by_punc (bool, optional): Defaults to True.

    Returns:
        list: list of text chunks
    """
    if len(text) <= max_sentence_size:
        return [add_punctuation(text)]

    # split text by punctuations if split_by_punc set to true
    chunks = None
    if split_by_punc:
        # first split by "ending" punctuations
        chunks = split_by_punctuation(
            text.strip(),
            puncs=['.', '!', '?', ':', '-', ';']
        )

        # if sentence is still to big, split by commas
        second_splits = []
        did_second_split = False
        for sentence in chunks:
            if len(sentence) > max_sentence_size:
                comma_splits = split_by_punctuation(
                    sentence.strip(), puncs=[',']
                )
                second_splits += comma_splits
                did_second_split = True
            else:
                second_splits.append(sentence.strip())

        if did_second_split:
            chunks = second_splits

        # if sentence is still to big by 20 word chunks
        third_splits = []
        did_third_split = False
        for sentence in chunks:
            if len(sentence) > max_sentence_size:
                chunk_split = split_by_chunk_size(sentence.strip(), 20)
                third_splits += chunk_split
                did_third_split = True
            else:
                third_splits.append(sentence.strip())

        if did_third_split:
            chunks = third_splits

        chunks = [add_punctuation(chunk) for chunk in chunks]
        return chunks


class Mimic2(TTS):

    def __init__(self, lang, config):
        super(Mimic2, self).__init__(
            lang, config, Mimic2Validator(self)
        )
        self.url = config['url']
        self.session = FuturesSession()
        chunk_size = config.get('chunk_size')
        self.chunk_size = \
            chunk_size if chunk_size is not None else 10

    def _save(self, data):
        """saves .wav files in tmp

        Args:
            data (byes): wav data
        """
        with open(self.filename, 'wb') as f:
            f.write(data)

    def _play(self, req):
        """play wav file after saving to tmp

        Args:
            req (object): requests object
        """
        if req.status_code == 200:
            self._save(req.content)
            play_wav(self.filename).communicate()
        else:
            LOG.error(
                '%s Http Error: %s for url: %s' %
                (req.status_code, req.reason, req.url))

    def _requests(self, chunks):
        """create asynchronous request list

        Args:
            chunks (list): list of text to synthesize

        Returns:
            list: list of FutureSession objects
        """
        reqs = []
        for chunk in chunks:
            if len(chunk) > 0:
                url = self.url + parse.quote(chunk)
                req_route = url + "&visimes=True"
                reqs.append(self.session.get(req_route, timeout=5))
        return reqs

    def visime(self, phonemes):
        """maps phonemes to visemes encoding

        Args:
            phonemes (list): list of tuples (phoneme, time_start)

        Returns:
            list: list of tuples (viseme_encoding, time_start)
        """
        visemes = []
        for pair in phonemes:
            if pair[0]:
                phone = pair[0].lower()
            else:
                # if phoneme doesn't exist use
                # this as placeholder since it
                # is the most common one "3"
                phone = 'z'
            vis = VISIMES.get(phone)
            vis_dur = float(pair[1])
            visemes.append((vis, vis_dur))
        return visemes

    def _normalized_numbers(self, sentence):
        """normalized numbers to word equivalent.

        Args:
            sentence (str): setence to speak

        Returns:
            stf: normalized sentences to speak
        """
        try:
            numbers = re.findall(r'-?\d+', sentence)
            normalized_num = [
                (num, pronounce_number(int(num)))
                for num in numbers
            ]
            for num, norm_num in normalized_num:
                sentence = sentence.replace(num, norm_num, 1)
        except TypeError:
            LOG.exception("type error in mimic2_tts.py _normalized_numbers()")
        return sentence

    def get_tts(self, sentence, wav_file):
        """request and play mimic2 wav audio

        Args:
            sentence (str): sentence to synthesize from mimic2
            ident (optional): Defaults to None.
        """
        sentence = self._normalized_numbers(sentence)

        # Use the phonetic_spelling mechanism from the TTS base class
        if self.phonetic_spelling:
            for word in re.findall(r"[\w']+", sentence):
                if word.lower() in self.spellings:
                    sentence = sentence.replace(word,
                                                self.spellings[word.lower()])

        chunks = sentence_chunker(sentence, self.chunk_size)
        try:
            for idx, req in enumerate(self._requests(chunks)):
                results = req.result().json()
                audio = base64.b64decode(results['audio_base64'])
                vis = results['visimes']
                with open(wav_file, 'wb') as f:
                    f.write(audio)
        except (ReadTimeout, ConnectionError, ConnectTimeout, HTTPError):
            raise RemoteTTSTimeoutException(
                "Mimic 2 remote server request timedout. falling back to mimic"
            )
        return (wav_file, vis)

    def save_phonemes(self, key, phonemes):
        """
            Cache phonemes

            Args:
                key:        Hash key for the sentence
                phonemes:   phoneme string to save
        """

        cache_dir = get_cache_directory("tts")
        pho_file = os.path.join(cache_dir, key + ".pho")
        try:
            with open(pho_file, "w") as cachefile:
                cachefile.write(json.dumps(phonemes))
        except Exception:
            LOG.exception("Failed to write {} to cache".format(pho_file))

    def load_phonemes(self, key):
        """
            Load phonemes from cache file.

            Args:
                Key:    Key identifying phoneme cache
        """
        pho_file = os.path.join(get_cache_directory("tts"), key + ".pho")
        if os.path.exists(pho_file):
            try:
                with open(pho_file, "r") as cachefile:
                    phonemes = json.load(cachefile)
                return phonemes
            except Exception as e:
                LOG.error("Failed to read .PHO from cache ({})".format(e))
        return None


class Mimic2Validator(TTSValidator):

    def __init__(self, tts):
        super(Mimic2Validator, self).__init__(tts)

    def validate_lang(self):
        # TODO
        pass

    def validate_connection(self):
        # TODO
        pass

    def get_tts_class(self):
        return Mimic2
