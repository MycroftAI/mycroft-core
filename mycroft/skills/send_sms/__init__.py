import subprocess
from os.path import dirname, join

from adapt.intent import IntentBuilder
from mycroft.messagebus.message import Message
from mycroft.skills.core import MycroftSkill
from mycroft.util.log import getLogger

__author__ = 'jdorleans'

LOGGER = getLogger(__name__)


class SendSMSSkill(MycroftSkill):
    DBUS_CMD = ["dbus-send", "--print-reply",
                "--dest=com.canonical.TelephonyServiceHandler",
                "/com/canonical/TelephonyServiceHandler",
                "com.canonical.TelephonyServiceHandler.SendMessage"]

    def __init__(self):
        super(SendSMSSkill, self).__init__(name="SendSMSSkill")
        self.contacts = {'jonathan': '12345678', 'ryan': '23456789',
                         'sean': '34567890'}  # TODO - Use API

    def initialize(self):
        self.load_vocab_files(join(dirname(__file__), 'vocab', 'en-us'))

        prefixes = ['tell', 'text', 'message']  # TODO - i10n
        self.__register_prefixed_regex(
            prefixes, "(?P<Contact>\w*) (?P<Message>.*)")

        intent = IntentBuilder("SendSMSIntent").require(
            "SendSMSKeyword").require("Contact").require("Message").build()
        self.register_intent(intent, self.handle_intent)

    def __register_prefixed_regex(self, prefixes, suffix_regex):
        for prefix in prefixes:
            self.register_regex(prefix + ' ' + suffix_regex)

    def handle_intent(self, message):
        try:
            contact = message.metadata.get("Contact").lower()

            if contact in self.contacts:
                number = self.contacts.get(contact)
                msg = message.metadata.get("Message")
                self.__send_sms(number, msg)
                self.__notify(contact, number, msg)

        except Exception as e:
            LOGGER.error("Error: {0}".format(e))

    def __send_sms(self, number, msg):
        cmd = list(self.DBUS_CMD)
        cmd.append("array:string:" + number)
        cmd.append("string:" + msg)
        cmd.append("string:ofono/ofono/account0")
        subprocess.call(cmd)

    def __notify(self, contact, number, msg):
        self.emitter.emit(
            Message(
                "send_sms",
                metadata={'contact': contact, 'number': number,
                          'message': msg}))

    def stop(self):
        pass


def create_skill():
    return SendSMSSkill()
