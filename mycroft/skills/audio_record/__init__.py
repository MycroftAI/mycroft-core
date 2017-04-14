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


import os
import sys
import subprocess
import time
import re

from adapt.intent import IntentBuilder
from adapt.tools.text.tokenizer import EnglishTokenizer
from os.path import dirname, join

from mycroft.skills.core import MycroftSkill
from mycroft.util.log import getLogger
from mycroft.util import play_wav

logger = getLogger(__name__)
__author__ = 'seanfitz'

class AudioRecordSkill(MycroftSkill):
    def __init__(self):
        super(AudioRecordSkill, self).__init__("AudioRecordSkill")
        self.file_path = self.config.get('filename')

    def is_current_language_supported(self):
        return self.lang == "en-US" or self.lang == "es" 

    def initialize(self):
	self.emitter.on('recognizer_loop:record_end', self.on_record_end)

        intent = IntentBuilder("AudioRecordSkillIntent").require(
            "AudioRecordSkillKeyword").build()
        self.register_intent(intent, self.handle_record)

    def handle_record(self, message):
        logger.debug("data=%s",message.data)
        self.session = message.data.get("session")
        self.speak_dialog(
            'audio.record.start',
            expect_response=True, 
            record_characteristics =
                { 'grammar' : False,
                  'record_filename' : self.file_path,
                  'session': self.session } )
        self.recording=True

    def on_record_end(self, message):
        if message.get('session') == self.session:
            self.speak_dialog( 'hecho' ) # TODO


def create_skill():
    return AudioRecordSkill()
