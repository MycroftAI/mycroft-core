from __future__ import absolute_import, division

from mycroft.stt import STT
from mycroft.util.log import LOG
from timeit import default_timer as timer
from os.path import exists, join, dirname
from mycroft.util.download import download
import tarfile
from time import sleep


class DeepSpeechSTT(STT):
    URL = "https://github.com/mozilla/DeepSpeech/releases/download/v0.1.0/" \
          "deepspeech-0.1.0-models.tar.gz"

    def __init__(self):
        super(DeepSpeechSTT, self).__init__()
        try:
            from deepspeech.model import Model
            self.Model = Model
        except ImportError:
            LOG.error("could not import deep speech, \n run pip install "
                      "deepspeech")
            raise

        self.BEAM_WIDTH = self.config.get("beam_width", 500)
        self.LM_WEIGHT = self.config.get("lm_weight", 1.75)
        self.WORD_COUNT_WEIGHT = self.config.get("word_count_weight", 1.00)
        self.VALID_WORD_COUNT_WEIGHT = self.config.get(
            "valid_word_count_weight", 1.00)

        # These constants are tied to the shape of the graph used
        # (changing them changes the geometry of the first layer), so make
        # sure you use the same constants that were used during training
        self.N_FEATURES = self.config.get("n_features", 26)
        self.N_CONTEXT = self.config.get("n_context", 9)

        self.model = self.config.get("model", "deepspeech_0.1.0")
        if self.model == "deepspeech_0.1.0":
            self.model = join(dirname(__file__), "deepspeech",
                              "output_graph.pb")
            auto_dl = True
        else:
            auto_dl = False

        self.lm = self.config.get("lm", join(dirname(__file__),
                                             "deepspeech",
                                             "lm.binary"))
        self.alphabet = self.config.get("alphabet", join(dirname(__file__),
                                                         "deepspeech",
                                                         "alphabet.txt"))
        self.trie = self.config.get("trie", join(dirname(__file__),
                                                 "deepspeech",
                                                 "trie"))
        self.downloaded = False
        self.dl = None

        if self.model_downloaded():
            self.load_model()
        elif auto_dl:
            LOG.info("Downloading model")
            self.download()
            while not self.downloaded:
                sleep(1)

            if not self.model_downloaded():
                raise AssertionError(self.model + " does not exist"
                                     ", download a pre-trained model with \n "
                                     "wget -O -" + DeepSpeechSTT.URL + "| "
                                     "tar xvfz -")
            self.load_model()

    def load_model(self):
        LOG.info('Loading model from file %s' % (self.model))
        model_load_start = timer()
        self.ds = self.Model(self.model, self.N_FEATURES, self.N_CONTEXT,
                             self.alphabet, self.BEAM_WIDTH)

        model_load_end = timer() - model_load_start
        LOG.debug('Loaded model in %0.3fs.' % (model_load_end))

        LOG.info('Loading language model from files %s %s' % (
            self.lm, self.trie))
        lm_load_start = timer()
        self.ds.enableDecoderWithLM(self.alphabet, self.lm, self.trie,
                                    self.LM_WEIGHT,
                                    self.WORD_COUNT_WEIGHT,
                                    self.VALID_WORD_COUNT_WEIGHT)
        lm_load_end = timer() - lm_load_start
        LOG.debug('Loaded language model in %0.3fs.' % (lm_load_end))

    def model_downloaded(self):
        if not exists(self.model) or not exists(self.lm) or not \
                exists(self.alphabet) or not exists(self.trie):
            return False
        return True

    def download(self):
        LOG.info("starting model download")
        target_folder = join(dirname(__file__), "deepspeech")
        self.dl = download(DeepSpeechSTT.URL, target_folder, self._extract)

    def _extract(self, target_folder=join(dirname(__file__), "deepspeech")):
        LOG.info("model downloaded, extracting files")
        file_path = join(target_folder, DeepSpeechSTT.URL.split("/")[-1])
        if not exists(file_path):
            raise AssertionError("file does not exist")
        if not file_path.endswith(".tar.gz") or not file_path.endswith(
                ".tar.bz2"):
            raise AssertionError("invalid file format")
        with tarfile.open(file_path) as tar:
            tar.extractall(target_folder)
        # os.remove(file_path)

        LOG.info("model ready")
        self.downloaded = True

    def execute(self, audio, language=None):
        self.lang = language or self.lang
        if not self.lang.startswith("en"):
            raise NotImplementedError("the only supported language is "
                                      "english")
        return self.ds.stt(audio.get_wav_data(), 16000)
