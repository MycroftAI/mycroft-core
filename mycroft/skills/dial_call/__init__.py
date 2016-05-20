import subprocess
from os.path import join, dirname

from adapt.intent import IntentBuilder
from mycroft.messagebus.message import Message
from mycroft.skills.core import MycroftSkill
from mycroft.util.log import getLogger

__author__ = 'jdorleans'

LOGGER = getLogger(__name__)


class DialCallSkill(MycroftSkill):
    DBUS_CMD = ["dbus-send", "--print-reply", "--dest=com.canonical.TelephonyServiceHandler",
                "/com/canonical/TelephonyServiceHandler", "com.canonical.TelephonyServiceHandler.StartCall"]

    def __init__(self):
        super(DialCallSkill, self).__init__(name="DialCallSkill")
        self.contacts = {'jonathan': '12345678', 'ryan': '23456789', 'sean': '34567890'}  # TODO - Use API

    def initialize(self):
        self.load_vocab_files(join(dirname(__file__), 'vocab', 'en-us'))

        prefixes = ['call', 'phone']  # TODO - i10n
        self.__register_prefixed_regex(prefixes, "(?P<Contact>.*)")

        intent = IntentBuilder("DialCallIntent").require("DialCallKeyword").require("Contact").build()
        self.register_intent(intent, self.handle_intent)

    def __register_prefixed_regex(self, prefixes, suffix_regex):
        for prefix in prefixes:
            self.register_regex(prefix + ' ' + suffix_regex)

    def handle_intent(self, message):
        try:
            contact = message.metadata.get("Contact").lower()

            if contact in self.contacts:
                number = self.contacts.get(contact)
                self.__call(number)
                self.__notify(contact, number)

        except Exception as e:
            LOGGER.error("Error: {0}".format(e))

    def __call(self, number):
        cmd = list(self.DBUS_CMD)
        cmd.append("string:" + number)
        cmd.append("string:ofono/ofono/account0")
        subprocess.call(cmd)

    def __notify(self, contact, number):
        self.emitter.emit(Message("dial_call", metadata={'contact': contact, 'number': number}))

    def stop(self):
        pass


def create_skill():
    return DialCallSkill()
