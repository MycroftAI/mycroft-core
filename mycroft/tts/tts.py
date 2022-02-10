from ovos_plugin_manager.tts import OVOSTTSFactory, load_tts_plugin
from ovos_plugin_manager.templates.tts import PlaybackThread, \
    TTS, TTSValidator, EMPTY_PLAYBACK_QUEUE_TUPLE
from mycroft.configuration import Configuration


class TTSFactory(OVOSTTSFactory):
    @staticmethod
    def create(config=None):
        config = config or Configuration.get()
        return OVOSTTSFactory.create(config)
