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
from os import path

from mycroft.tts import TTS, TTSValidator

__author__ = 'jarbas'


class PicoEngine(object):
    """
    A text to speech engine class based on svox pico tts.
    """

    def __init__(self, language="en-GB", lang_dir=None):
        """
        Initialize engine with the given language.
        Currently available languages are: en-GB, en-US, de-DE, es-ES, fr-FR, it-IT
        lang_dir: An optional language directory where the requested language
        definition files can be found.
        """
        import ctts
        self.ctts = ctts
        _LANG_DIR = path.join(path.abspath(path.dirname(__file__)),
                              "languages")
        if not path.isdir(_LANG_DIR):
            from sys import prefix

            _LANG_DIR = path.join(prefix, "languages")

        lang_dirs = ["/usr/share/pico/lang/", _LANG_DIR]
        if lang_dir:
            lang_dirs.insert(0, lang_dir)

        self.__e = None
        for ldir in lang_dirs:
            try:
                self.__e = self.ctts.engine_create(language_dir=ldir,
                                                   language=language)
            except RuntimeError as ex:
                pass  # Try next directory to find language...
            if self.__e:
                break

        if self.__e is None:
            raise RuntimeError(
                "Could not instantiate TTS engine with language " + language)

    def speak(self, text, callback=None):
        """
        Speak some text using the initialized speech engine.
        callback: optinal callback should follow the signature
        (format, audio, fin) -> Boolean
        format: is the format of the PCM data within the audio buffer
        audio: pcm data of the generated speech
        fin: When True, indicates that this is the last audio chunk of the stream
        If the return value evaluates to false then the speech generation is stopped.

        If a callback is not supplied, the PCM audio data for the entire text are returned.
        """
        data = []
        if callback is None:
            callback = lambda format, audio, fin: data.append(audio)
        self.ctts.engine_speak(self.__e, text, callback)
        if data:
            return b''.join(data)

    @property
    def rate(self):
        """
        Get/Set the speech rate (speed).
        """
        return self.get_property("rate")

    @rate.setter
    def rate(self, value):
        i = self.set_property("rate", value)
        if i != value:
            raise ValueError("Requested rate is beyond the acceptable limits")

    @property
    def pitch(self):
        """
        Get/Set voice pitch.
        """
        return self.get_property("pitch")

    @pitch.setter
    def pitch(self, value):
        i = self.set_property("pitch", value)
        if i != value:
            raise ValueError(
                "Requested pitch is beyond the acceptable limits")

    @property
    def volume(self):
        """
        Get/Set voice volume.
        """
        return self.get_property("volume")

    @volume.setter
    def volume(self, value):
        i = self.set_property("volume", value)
        if i != value:
            raise ValueError(
                "Requested volume is beyond the acceptable limits")

    def set_property(self, property_name, value):
        """
        Set an engine property. Returns the effective property value.
        """
        return self.ctts.engine_set_property(self.__e, property_name, value)

    def get_property(self, property_name):
        """
        Get an engine property value.
        """
        return self.ctts.engine_get_property(self.__e, property_name)

    def stop(self):
        """
        Stop speech synthesis.
        """
        return self.ctts.engine_stop(self.__e)


class Pico(TTS):
    def __init__(self, lang, voice):
        super(Pico, self).__init__(lang, voice, PicoValidator(self))
        self.engine = PicoEngine(self.lang)
        self.type = "raw"

    def execute(self, sentence, output="/tmp/pico_tts.raw"):
        self.begin_audio()
        audio = self.engine.speak(unicode(sentence))
        with open(output, "wb") as outfile:
            outfile.write(audio)
        subprocess.call(
            ['aplay', '--rate=16000', "--channels=1", "--format=S16_LE",
             output])
        self.end_audio()


class PicoValidator(TTSValidator):
    def __init__(self, tts):
        super(PicoValidator, self).__init__(tts)

    def validate_lang(self):
        # TODO
        pass

    def validate_connection(self):
        pass

    def get_tts_class(self):
        return Pico
