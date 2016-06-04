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


import logging

from mycroft.configuration.config import ConfigurationManager
from mycroft.tts import espeak_tts
from mycroft.tts import fa_tts
from mycroft.tts import google_tts
from mycroft.tts import mary_tts
from mycroft.tts import mimic_tts
from mycroft.tts import spdsay_tts

__author__ = 'jdorleans'


def create():
    """
    Factory method to create a TTS engine based on configuration.

    The configuration file ``defaults.ini`` contains a ``tts`` section with
    the name of a TTS module to be read by this method.

    [tts]

    module = <engine_name>
    """

    logging.basicConfig()
    config = ConfigurationManager.get().get('tts')
    name = config.get('module')
    lang = config.get(name + '.lang', None)
    voice = config.get(name + '.voice')

    if name == mimic_tts.NAME:
        tts = mimic_tts.Mimic(lang, voice)
        mimic_tts.MimicValidator().validate(tts)
    elif name == google_tts.NAME:
        tts = google_tts.GoogleTTS(lang, voice)
        google_tts.GoogleTTSValidator().validate(tts)
    elif name == mary_tts.NAME:
        tts = mary_tts.MaryTTS(lang, voice, config[name + '.url'])
        mary_tts.MaryTTSValidator().validate(tts)
    elif name == fa_tts.NAME:
        tts = fa_tts.FATTS(lang, voice, config[name + '.url'])
        fa_tts.FATTSValidator().validate(tts)
    elif name == espeak_tts.NAME:
        tts = espeak_tts.ESpeak(lang, voice)
        espeak_tts.ESpeakValidator().validate(tts)
    else:
        tts = spdsay_tts.SpdSay(lang, voice)
        spdsay_tts.SpdSayValidator().validate(tts)
    return tts
