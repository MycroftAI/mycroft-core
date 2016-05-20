from adapt.intent import IntentBuilder
from os.path import join, dirname

from mycroft.configuration.config import RemoteConfiguration
from mycroft.identity import IdentityManager
from mycroft.skills.core import MycroftSkill


class CerberusConfigSkill(MycroftSkill):
    def __init__(self):
        MycroftSkill.__init__(self, "CerberusConfigSkill")

    def initialize(self):
        intent = IntentBuilder("update_cerberus_config")\
            .require("UpdateConfigurationPhrase")\
            .build()
        self.load_data_files(join(dirname(__file__)))
        self.register_intent(intent, handler=self.handle_update_request)

    def handle_update_request(self, message):
        identity = IdentityManager().get()
        if not identity.owner:
            self.speak_dialog("not.paired")
        else:
            rc = RemoteConfiguration()
            rc.update()
            self.speak_dialog("config.updated")


def create_skill():
    return CerberusConfigSkill()
