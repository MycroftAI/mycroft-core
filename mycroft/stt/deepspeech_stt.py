from __future__ import absolute_import, division

from mycroft.stt import STT
from mycroft.util.log import LOG
from timeit import default_timer as timer
from os.path import exists, join, dirname
from mycroft.util.download import download


class DeepSpeechSTT(STT):
    URL = "https://github.com/mozilla/DeepSpeech/releases/download/v0.1.0/deepspeech-0.1.0-models.tar.gz"

    def __init__(self):
        super(STT, self).__init__()
        try:
            from deepspeech.model import Model
        except ImportError:
            LOG.error("could not import deep speech, \n run pip install "
                      "deepspeech")

        # These constants control the beam search decoder
        print self.config
        # Beam width used in the CTC decoder when building candidate transcriptions
        self.BEAM_WIDTH = self.config.get("beam_width", 500)

        # The alpha hyperparameter of the CTC decoder. Language Model weight
        self.LM_WEIGHT = self.config.get("lm_weight", 1.75)

        # The beta hyperparameter of the CTC decoder. Word insertion weight (penalty)
        self.WORD_COUNT_WEIGHT = self.config.get("word_count_weight", 1.00)

        # Valid word insertion weight. This is used to lessen the word insertion penalty
        # when the inserted word is part of the vocabulary
        self.VALID_WORD_COUNT_WEIGHT = self.config.get(
            "valid_word_count_weight", 1.00)

        # These constants are tied to the shape of the graph used (changing them changes
        # the geometry of the first layer), so make sure you use the same constants that
        # were used during training

        # Number of MFCC features to use
        self.N_FEATURES = self.config.get("n_features", 26)

        # Size of the context window used for producing timesteps in the input vector
        self.N_CONTEXT = self.config.get("n_context", 9)

        self.model = self.config.get("model", join(dirname(__file__),
                                                   "deepspeech",
                                                   "output_graph.pb"))
        self.lm = self.config.get("lm", join(dirname(__file__),
                                             "deepspeech",
                                             "lm.binary"))
        self.alphabet = self.config.get("alphabet", join(dirname(__file__),
                                                         "deepspeech",
                                                         "alphabet.txt"))
        self.trie = self.config.get("trie", join(dirname(__file__),
                                                 "deepspeech",
                                                 "trie"))

        if self.config.get("auto_download", False):
            self.download()

        if not self.model or not exists(self.model):
            raise AssertionError(self.model + " does not exist, download a "
                                              "pre-trained model with \n wget -O - https://github.com/mozilla/DeepSpeech/releases/download/v0.1.0/deepspeech-0.1.0-models.tar.gz | tar xvfz -")

        if not exists(self.lm):
            raise AssertionError("language model does not exist")

        if not exists(self.alphabet):
            raise AssertionError("alphabet configuration file does not exist")

        if not exists(self.trie):
            raise AssertionError("language model trie does not exist")

        LOG.info('Loading model from file %s' % (self.model))
        model_load_start = timer()
        self.ds = Model(self.model, self.N_FEATURES, self.N_CONTEXT,
                        self.alphabet, self.BEAM_WIDTH)
        model_load_end = timer() - model_load_start
        LOG.info('Loaded model in %0.3fs.' % (model_load_end))

        if self.lm and self.trie:
            LOG.info('Loading language model from files %s %s' % (
                self.lm, self.trie))
            lm_load_start = timer()
            self.ds.enableDecoderWithLM(self.alphabet, self.lm, self.trie,
                                        self.LM_WEIGHT,
                                        self.WORD_COUNT_WEIGHT,
                                        self.VALID_WORD_COUNT_WEIGHT)
            lm_load_end = timer() - lm_load_start
            LOG.info('Loaded language model in %0.3fs.' % (lm_load_end))

    def download(self):
        download(DeepSpeechSTT.URL, join(dirname(__file__), "deepspeech"))
        # TODO extract

    def execute(self, audio, language=None):
        self.lang = language or self.lang
        return self.ds.stt(audio.get_wav_data(), 16000)
