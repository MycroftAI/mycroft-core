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
import tempfile
import time

import sys
from tempfile import NamedTemporaryFile

import os
from os.path import dirname, exists, join, abspath, expanduser, isdir, isfile

from os import mkdir, getcwd, chdir
from time import time as get_time

from mycroft.configuration import Configuration
from subprocess import Popen, PIPE, call
from threading import Thread

from mycroft.util.log import LOG


RECOGNIZER_DIR = join(abspath(dirname(__file__)), "recognizer")


class HotWordEngine(object):
    def __init__(self, key_phrase="hey mycroft", config=None, lang="en-us"):
        self.key_phrase = str(key_phrase).lower()
        # rough estimate 1 phoneme per 2 chars
        self.num_phonemes = len(key_phrase) / 2 + 1
        if config is None:
            config = Configuration.get().get("hot_words", {})
            config = config.get(self.key_phrase, {})
        self.config = config
        self.listener_config = Configuration.get().get("listener", {})
        self.lang = str(self.config.get("lang", lang)).lower()

    def found_wake_word(self, frame_data):
        return False

    def update(self, chunk):
        pass


class PocketsphinxHotWord(HotWordEngine):
    def __init__(self, key_phrase="hey mycroft", config=None, lang="en-us"):
        super(PocketsphinxHotWord, self).__init__(key_phrase, config, lang)
        # Hotword module imports
        from pocketsphinx import Decoder
        # Hotword module config
        module = self.config.get("module")
        if module != "pocketsphinx":
            LOG.warning(
                str(module) + " module does not match with "
                              "Hotword class pocketsphinx")
        # Hotword module params
        self.phonemes = self.config.get("phonemes", "HH EY . M AY K R AO F T")
        self.num_phonemes = len(self.phonemes.split())
        self.threshold = self.config.get("threshold", 1e-90)
        self.sample_rate = self.listener_config.get("sample_rate", 1600)
        dict_name = self.create_dict(self.key_phrase, self.phonemes)
        config = self.create_config(dict_name, Decoder.default_config())
        self.decoder = Decoder(config)

    def create_dict(self, key_phrase, phonemes):
        (fd, file_name) = tempfile.mkstemp()
        words = key_phrase.split()
        phoneme_groups = phonemes.split('.')
        with os.fdopen(fd, 'w') as f:
            for word, phoneme in zip(words, phoneme_groups):
                f.write(word + ' ' + phoneme + '\n')
        return file_name

    def create_config(self, dict_name, config):
        model_file = join(RECOGNIZER_DIR, 'model', self.lang, 'hmm')
        if not exists(model_file):
            LOG.error('PocketSphinx model not found at ' + str(model_file))
        config.set_string('-hmm', model_file)
        config.set_string('-dict', dict_name)
        config.set_string('-keyphrase', self.key_phrase)
        config.set_float('-kws_threshold', float(self.threshold))
        config.set_float('-samprate', self.sample_rate)
        config.set_int('-nfft', 2048)
        config.set_string('-logfn', '/dev/null')
        return config

    def transcribe(self, byte_data, metrics=None):
        start = time.time()
        self.decoder.start_utt()
        self.decoder.process_raw(byte_data, False, False)
        self.decoder.end_utt()
        if metrics:
            metrics.timer("mycroft.stt.local.time_s", time.time() - start)
        return self.decoder.hyp()

    def found_wake_word(self, frame_data):
        hyp = self.transcribe(frame_data)
        return hyp and self.key_phrase in hyp.hypstr.lower()


class PreciseHotword(HotWordEngine):
    def __init__(self, key_phrase="hey mycroft", config=None, lang="en-us"):
        super(PreciseHotword, self).__init__(key_phrase, config, lang)
        self.update_freq = 24  # in hours

        precise_config = Configuration.get()['precise']
        self.dist_url = precise_config['dist_url']
        self.models_url = precise_config['models_url']
        self.exe_name = 'precise-stream'

        model_name, model_path = self.get_model_info()

        exe_file = self.find_download_exe()
        LOG.info('Found precise executable: ' + exe_file)
        self.update_model(model_name, model_path)

        args = [exe_file, model_path, '1024']
        self.proc = Popen(args, stdin=PIPE, stdout=PIPE)
        self.has_found = False
        self.cooldown = 20
        t = Thread(target=self.check_stdout)
        t.daemon = True
        t.start()

    def get_model_info(self):
        ww = Configuration.get()['listener']['wake_word']
        model_name = ww.replace(' ', '-') + '.pb'
        model_folder = expanduser('~/.mycroft/precise')
        if not isdir(model_folder):
            mkdir(model_folder)
        model_path = join(model_folder, model_name)
        return model_name, model_path

    def find_download_exe(self):
        try:
            if call('command -v ' + self.exe_name,
                    shell=True, stdout=PIPE) == 0:
                return self.exe_name
        except OSError:
            pass

        precise_folder = expanduser('~/.mycroft/precise')
        if isfile(join(precise_folder, 'precise-stream')):
            os.remove(join(precise_folder, 'precise-stream'))

        exe_file = join(precise_folder, 'precise-stream', 'precise-stream')
        if isfile(exe_file):
            return exe_file

        import platform
        import stat

        def snd_msg(cmd):
            """Send message to faceplate"""
            Popen('echo "' + cmd + '" > /dev/ttyAMA0', shell=True)

        arch = platform.machine()

        url = self.dist_url + arch + '/precise-stream.tar.gz'
        tar_file = NamedTemporaryFile().name + '.tar.gz'

        snd_msg('mouth.text=Updating Listener...')
        cur_dir = getcwd()
        chdir(precise_folder)
        try:
            self.download(url, tar_file)
            call(['tar', '-xzvf', tar_file])
        finally:
            chdir(cur_dir)
            snd_msg('mouth.reset')

        if not isfile(exe_file):
            raise RuntimeError('Could not extract file: ' + exe_file)
        os.chmod(exe_file, os.stat(exe_file).st_mode | stat.S_IEXEC)
        return exe_file

    @staticmethod
    def download(url, filename):
        import shutil

        # python 2/3 compatibility
        if sys.version_info[0] >= 3:
            from urllib.request import urlopen
        else:
            from urllib2 import urlopen
        LOG.info('Downloading: ' + url)
        req = urlopen(url)
        with open(filename, 'wb') as fp:
            shutil.copyfileobj(req, fp)
        LOG.info('Download complete.')

    def update_model(self, name, file_name):
        if isfile(file_name):
            stat = os.stat(file_name)
            if get_time() - stat.st_mtime < self.update_freq * 60 * 60:
                return
        name = name.replace(' ', '%20')
        url = self.models_url + name
        self.download(url, file_name)
        self.download(url + '.params', file_name + '.params')

    def check_stdout(self):
        while True:
            line = self.proc.stdout.readline()
            if self.cooldown > 0:
                self.cooldown -= 1
                self.has_found = False
                continue
            self.has_found = float(line) > 0.5

    def update(self, chunk):
        self.proc.stdin.write(chunk)
        self.proc.stdin.flush()

    def found_wake_word(self, frame_data):
        if self.has_found and self.cooldown == 0:
            self.cooldown = 20
            return True
        return False


class SnowboyHotWord(HotWordEngine):
    def __init__(self, key_phrase="hey mycroft", config=None, lang="en-us"):
        super(SnowboyHotWord, self).__init__(key_phrase, config, lang)
        # Hotword module imports
        from snowboydecoder import HotwordDetector
        # Hotword module config
        module = self.config.get("module")
        if module != "snowboy":
            LOG.warning(module + " module does not match with Hotword class "
                                 "snowboy")
        # Hotword params
        models = self.config.get("models", {})
        paths = []
        for key in models:
            paths.append(models[key])
        sensitivity = self.config.get("sensitivity", 0.5)
        self.snowboy = HotwordDetector(paths,
                                       sensitivity=[sensitivity] * len(paths))
        self.lang = str(lang).lower()
        self.key_phrase = str(key_phrase).lower()

    def found_wake_word(self, frame_data):
        wake_word = self.snowboy.detector.RunDetection(frame_data)
        return wake_word == 1


class HotWordFactory(object):
    CLASSES = {
        "pocketsphinx": PocketsphinxHotWord,
        "precise": PreciseHotword,
        "snowboy": SnowboyHotWord
    }

    @staticmethod
    def create_hotword(hotword="hey mycroft", config=None, lang="en-us"):
        LOG.info("creating " + hotword)
        if not config:
            config = Configuration.get().get("hotwords", {})
        module = config.get(hotword).get("module", "pocketsphinx")
        config = config.get(hotword, {"module": module})
        clazz = HotWordFactory.CLASSES.get(module)
        try:
            return clazz(hotword, config, lang=lang)
        except Exception:
            LOG.exception('Could not create hotword. Falling back to default.')
            return HotWordFactory.CLASSES['pocketsphinx']()
