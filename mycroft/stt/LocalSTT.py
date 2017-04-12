from . import STT

from mycroft.configuration import ConfigurationManager
from mycroft.util.log import getLogger
from pocketsphinx import Decoder
from mycroft.client.speech.local_recognizer import LocalRecognizer

LOG = getLogger("LocalSTT")

class LocalSTT(STT):
    def __init__(self):
        super(LocalSTT, self).__init__()
        self.default_lang = str(ConfigurationManager.get().get("lang", "en-US"))
        self.sample_rate = 16000
        self.lang = self.default_lang

    def execute(self, audio, language=None ):
        LOG.debug("LocalSTT: execute")
#        self.lang = language
#	if not self.lang:
#           self.lang = self.default_lang

        # TODO: remove, only for debug
	newFile = open("/home/pma/actual/mic.tmp.wav", "wb")
        wav_data=audio.get_wav_data()
        newFile.write(wav_data)
	newFile.close()

#	LocalRecognizer.decoder.set_search('command')
#        LocalRecognizer.decoder.start_utt()
#        LocalRecognizer.decoder.process_raw( audio.frame_data, False, True ) # full_utt=True
#        hyp =  LocalRecognizer.decoder.hyp()
#        LocalRecognizer.decoder.end_utt()

#        res = hyp.hypstr.lower()
        res="dummy"
        LOG.debug("LocalSTT: res="+res)
        return res

    def create_config(self):
        config = Decoder.default_config()
        config.set_string('-hmm', '/usr/share/pocketsphinx/model/es/es' )
        config.set_string('-dict', '/home/pma/varios/mycroft/model/es.dict' )
        config.set_string('-fdict', '/usr/share/pocketsphinx/model/es/es/noisedict' )
        config.set_string('-featparams', '/usr/share/pocketsphinx/model/es/es/feat.params' )
        config.set_string('-mdef', '/usr/share/pocketsphinx/model/es/es/mdef' )
        config.set_string('-mean', '/usr/share/pocketsphinx/model/es/es/means' )
        config.set_string('-mixw', '/usr/share/pocketsphinx/model/es/es/mixture_weights' )
        config.set_string('-tmat', '/usr/share/pocketsphinx/model/es/es/transition_matrices' )
        config.set_string('-sendump', '/usr/share/pocketsphinx/model/es/es/sendump' )
        config.set_string('-var', '/usr/share/pocketsphinx/model/es/es/variances' )
#        config.set_string('-lm', '/home/pma/varios/mycroft/model/es-current.lm' ) 
        config.set_string('-jsgf', '/home/pma/varios/mycroft/model/es-current.jsgf' )
        config.set_float('-samprate', self.sample_rate)
#        config.set_string('-logfn', '/dev/null')
        config.set_string('-logfn', 'scripts/logs/decoder.log' )
        config.set_string('-cmninit', '56.29,-10.65,5.53,13.07,6.90,3.92,-5.11,8.41,-2.68,4.40,2.33,0.98,-2.88' ) # TODO: this must be in config
        return config


