# Copyright 2016 Mycroft AI, Inc.
#
# This file is part of Mycroft Core.
#
# Mycroft Core is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Mycroft Core is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Mycroft Core.  If not, see <http://www.gnu.org/licenses/>.


import subprocess

from adapt.intent import IntentBuilder
from os.path import dirname, join

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
        self.load_vocab_files(join(dirname(__file__), 'vocab', self.lang))
        self.load_regex_files(join(dirname(__file__), 'regex', self.lang))
        intent = IntentBuilder("SendSMSIntent").require(
            "SendSMSKeyword").require("Contact").require("Message").build()
        self.register_intent(intent, self.handle_intent)

    def handle_intent(self, message):
        try:
            contact = message.data.get("Contact").lower()

            if contact in self.contacts:
                number = self.contacts.get(contact)
                msg = message.data.get("Message")
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
            Message("send_sms", {
                'contact': contact, 'number': number, 'message': msg
            }))

    def stop(self):
        pass


def create_skill():
    return SendSMSSkill()
