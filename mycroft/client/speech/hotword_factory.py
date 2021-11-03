from mycroft.configuration import Configuration
from ovos_plugin_manager.wakewords import OVOSWakeWordFactory, \
    load_wake_word_plugin, find_wake_word_plugins
from ovos_plugin_manager.templates.hotwords import HotWordEngine


class HotWordFactory(OVOSWakeWordFactory):
    @classmethod
    def create_hotword(cls, hotword="hey mycroft", config=None,
                       lang="en-us", loop=None):
        if not config:
            config = Configuration.get()['hotwords']
        return OVOSWakeWordFactory.create_hotword(hotword, config, lang, loop)
