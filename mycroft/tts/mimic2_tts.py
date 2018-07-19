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

from mycroft.tts import TTSValidator
from mycroft.tts.remote_tts import RemoteTTS
from mycroft.util.log import LOG
from mycroft.util import play_wav
from requests_futures.sessions import FuturesSession
from urllib import parse
import math


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


def split_by_punctuation(text, chunk_size):
    """split text by punctuations
        i.e "hello, world" -> ["hello", "world"]

    Args:
        text (str): text to split
        chunk_size (int): size of each chunk

    Returns:
        list: list of sentence chunk
    """
    punctuations = [',', '.', '-', '?', '!', ':', ';']
    text_list = text.split()
    splits = None
    if len(text_list) >= chunk_size:
        for punc in punctuations:
            if punc in text:
                splits = text.split(punc)
                break

    # TODO: check if splits are to small, combined them

    return splits


def add_punctuation(text):
    """add punctuation at the end of each chunk. Mimic2
    expects a form of punctuation
    """
    punctuations = ['.', '?', '!']
    if len(text) < 1:
        return text
    if len(text) < 10:
        if text[-1] in punctuations:
            if text[-1] != ".":
                return text[:-1] + "."
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
    text_list = text.split()
    # if initial text is 1.3 times chunk size, no need to split
    # if the chracter count is less then 55
    if len(text_list) <= chunk_size * 1.3:
        if len(text) < 55:
            return [text]

    # split text by punctuations if split_by_punc set to true
    punc_splits = None
    if split_by_punc:
        punc_splits = split_by_punctuation(text, chunk_size)

    # split text by chunk size
    chunks = []
    if punc_splits:
        for sentence in punc_splits:
            sentence = sentence.strip()
            chunks += split_by_chunk_size(sentence, chunk_size)
    # split text by chunk size
    else:
        chunks += split_by_chunk_size(text, chunk_size)

    chunks = [add_punctuation(chunk) for chunk in chunks]

    return chunks


class Mimic2(RemoteTTS):
    PARAMS = {'accept': 'audio/wav'}

    def __init__(self, lang, config):
        super(Mimic2, self).__init__(
            lang, config, config['url'],
            config['api_path'], Mimic2Validator(self)
        )
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

    def build_request_params(self, sentence):
        """RemoteTTS expects this method as abc.abstractmethod"""
        pass

    def _requests(self, chunks):
        """create asynchronous request list

        Args:
            chunks (list): list of text to synthesize

        Returns:
            list: list of FutureSession objects
        """
        reqs = []
        for chunk in chunks:
            req_route = \
                self.url + self.api_path + parse.quote(chunk)
            reqs.append(self.session.get(req_route))
        return reqs

    def execute(self, sentence, ident=None):
        """request and play mimic2 wav audio

        Args:
            sentence (str): sentence to synthesize from mimic2
            ident (optional): Defaults to None.
        """
        chunks = sentence_chunker(sentence, self.chunk_size)
        for req in self._requests(chunks):
            try:
                res = req.result()
                self.begin_audio()
                self._play(res)
            except Exception as e:
                LOG.error(e)
            finally:
                self.end_audio()


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
