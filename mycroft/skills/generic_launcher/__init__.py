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


class GenericLauncherSkill(MycroftSkill):
    def __init__(self):
        MycroftSkill.__init__(self, "GenericLauncherSkill")

    def is_current_language_supported(self):
        return self.lang == "es" 

    def initialize(self):
        launch_intent = IntentBuilder(
            "GenericLauncherSkillIntent").require("LaunchKeyword").build()
        self.register_intent(launch_intent, self.handle_intent)
	self.DEVNULL = open(os.devnull, 'wb')
	self.spotify_popen = None
        self.emitter.on('recognizer_loop:record_end', self.on_record_end)
        self.recording=False
	self.avisa_re=re.compile(r'avisa en (.*?) minutos?')

    def handle_intent(self, message):
        logger.debug("message.data=%s",str(message.data))
        utterance = message.data.get("utterance")

	if utterance == u'pon m\xfasica':
          self.handle_pon_musica()

	elif utterance == u'apaga la m\xfasica':
    	  self.handle_apaga_la_musica()

	elif utterance.startswith(u'avisa'):
    	  self.handle_avisa(utterance)

	  
    def handle_pon_musica(self):
        logger.debug("poniendo musica ...")
        if self.spotify_popen and self.spotify_popen.poll() == None:
            return
	self.spotify_popen = subprocess.Popen("spotify",stdout=self.DEVNULL,stderr=self.DEVNULL)
	time.sleep(5)
	subprocess.call(["qdbus","org.mpris.MediaPlayer2.spotify","/org/mpris/MediaPlayer2","org.mpris.MediaPlayer2.Player.OpenUri","spotify:artist:4sD9znwiVFx9cgRPZ42aQ1"], stdout=self.DEVNULL, stderr=self.DEVNULL)


    def handle_apaga_la_musica(self):
        logger.debug("apagando musica ...")
        if self.spotify_popen:
	    self.spotify_popen.terminate()


    word2nbr_data = {
      "un" : 1,
      "dos" : 2,
      "tres" : 3,
      "cuatro" : 4,
      "cinco" : 5,
      "seis" : 6,
      "siete" : 7,
      "ocho" : 8,
      "nueve" : 9,
      "diez" : 10 }

    def word2nbr(self,word):
        return self.word2nbr_data.get(word)

    def handle_avisa(self,cmnd):
        logger.debug("avisa:cmnd=%s",cmnd)
        m = self.avisa_re.match(cmnd)
        if not m:
            return

        self.wait_intv_txt=m.group(1)
        intv=self.word2nbr(self.wait_intv_txt)
        if not intv:
            return
        self.wait_intv=60*intv
        logger.debug("avisa:wait=%s",self.wait_intv)

        self.speak(u'que debo avisar?', expect_response=True, 
            record_characteristics =
                { 'no_stt' : True, 
                  'record_filename' : '/tmp/prueba.wav' } )
        self.recording=True

    def on_record_end(self, message):
        if self.recording:
            self.recording=False
            self.speak(u'entendido, en %s minutos aviso'%self.wait_intv_txt)
	    # play_wav("/tmp/prueba.wav")

            time.sleep(self.wait_intv)

	    play_wav("/tmp/prueba.wav")

	

def create_skill():
    return GenericLauncherSkill()
