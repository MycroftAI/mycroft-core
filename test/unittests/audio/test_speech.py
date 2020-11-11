# Copyright 2017 Mycroft AI Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
import unittest
import unittest.mock as mock

from shutil import rmtree
from threading import Thread
from time import sleep

from os.path import exists

import mycroft.audio.speech as speech
from mycroft.messagebus import Message
from mycroft.tts.remote_tts import RemoteTTSTimeoutException

"""Tests for speech dispatch service."""


tts_mock = mock.Mock()


def setup_mocks(config_mock, tts_factory_mock):
    """Do the common setup for the mocks."""
    config_mock.get.return_value = {}

    tts_factory_mock.create.return_value = tts_mock
    config_mock.reset_mock()
    tts_factory_mock.reset_mock()
    tts_mock.reset_mock()


@mock.patch('mycroft.audio.speech.Configuration')
@mock.patch('mycroft.audio.speech.TTSFactory')
class TestSpeech(unittest.TestCase):
    def test_life_cycle(self, tts_factory_mock, config_mock):
        """Ensure the init and shutdown behaves as expected."""
        setup_mocks(config_mock, tts_factory_mock)
        bus = mock.Mock()
        speech.init(bus)

        self.assertTrue(tts_factory_mock.create.called)
        bus.on.assert_any_call('mycroft.stop', speech.handle_stop)
        bus.on.assert_any_call('mycroft.audio.speech.stop',
                               speech.handle_stop)
        bus.on.assert_any_call('speak', speech.handle_speak)

        speech.shutdown()
        self.assertTrue(tts_mock.playback.stop.called)
        self.assertTrue(tts_mock.playback.join.called)

    def test_speak(self, tts_factory_mock, config_mock):
        """Ensure the speech handler executes the tts."""
        setup_mocks(config_mock, tts_factory_mock)
        bus = mock.Mock()
        speech.init(bus)

        speak_msg = Message('speak',
                            data={'utterance': 'hello there. world',
                                  'listen': False},
                            context={'ident': 'a'})
        speech.handle_speak(speak_msg)
        tts_mock.execute.assert_has_calls(
                [mock.call('hello there.', 'a', False, None),
                 mock.call('world', 'a', False, None)])

    def test_speak_sound_skill_conf(self, tts_factory_mock, config_mock):
        """Ensure the speech handler executes the sound instead of
        the utterance. with skill exception set to force sound"""
        setup_mocks(config_mock, tts_factory_mock)
        bus = mock.Mock()
        speech.init(bus)
        speech.audio_files = {'acknowledge': "snd/acknowledge.mp3"}
        config_mock.get.return_value =\
            {'skills': {'skills_pref_sound': ['SpeechSkill']}}

        speak_msg = Message('speak',
                            data={'utterance': 'hello there. world',
                                  'listen': False,
                                  'meta': {'skill': 'SpeechSkill',
                                           'outcome_type': 'acknowledge'}
                                  },
                            context={'ident': 'a'})
        speech.handle_speak(speak_msg)
        tts_mock.execute.assert_has_calls(
                [mock.call('hello there. world', 'a', False,
                           'snd/acknowledge.mp3')])

    @mock.patch('os.path')
    def test_speak_custom_sound(self, pth_mock, tts_factory_mock, config_mock):
        """Ensure the speech handler executes the custom sound instead of
        the utterance. When custom sound is set and conf wants to play sound"""
        setup_mocks(config_mock, tts_factory_mock)
        bus = mock.Mock()
        speech.init(bus)
        speech.audio_files = {'acknowledge': "snd/acknowledge.mp3"}
        pth_mock.exists.return_value = True
        config_mock.get.return_value =\
            {'skills': {'skills_pref_sound': ['SpeechSkill']}}

        speak_msg = Message('speak',
                            data={'utterance': 'hello there. world',
                                  'custom_sound': 'snd.wav',
                                  'listen': False,
                                  'meta': {'skill': 'SpeechSkill',
                                           'outcome_type': 'acknowledge'}
                                  },
                            context={'ident': 'a'})
        speech.handle_speak(speak_msg)
        tts_mock.execute.assert_has_calls(
                [mock.call('hello there. world', 'a', False, 'snd.wav')])

    @mock.patch('os.path')
    def test_speak_force_custom_sound(self, path_mock,
                                      tts_factory_mock, config_mock):
        """Ensure the speech handler executes the custom sound instead of
        the utterance. When custom sound is set and no utterance"""
        setup_mocks(config_mock, tts_factory_mock)
        bus = mock.Mock()
        speech.init(bus)
        speech.audio_files = {'acknowledge': "snd/acknowledge.mp3"}
        path_mock.exists.return_value = True

        speak_msg = Message('speak',
                            data={'custom_sound': 'snd.wav',
                                  'listen': False,
                                  'meta': {'skill': 'SpeechSkill'}
                                  },
                            context={'ident': 'a'})
        speech.handle_speak(speak_msg)
        tts_mock.execute.assert_has_calls(
                [mock.call(None, 'a', False, 'snd.wav')])

    def test_speak_sound_global_conf(self, tts_factory_mock, config_mock):
        """Ensure the speech handler executes the sound instead of
        the utterance, with global parameter to force sound."""
        setup_mocks(config_mock, tts_factory_mock)
        bus = mock.Mock()
        speech.init(bus)
        speech.audio_files = {'acknowledge': "snd/acknowledge.mp3"}
        config_mock.get.return_value = {'always_pref_sound': True}

        speak_msg = Message('speak',
                            data={'utterance': 'hello there. world',
                                  'listen': False,
                                  'meta': {'skill': 'SpeechSkill',
                                           'outcome_type': 'acknowledge'}
                                  },
                            context={'ident': 'a'})
        speech.handle_speak(speak_msg)
        tts_mock.execute.assert_has_calls(
                [mock.call('hello there. world', 'a', False,
                           'snd/acknowledge.mp3')])

    @mock.patch('mycroft.audio.speech.Mimic')
    def test_fallback_tts(self, mimic_cls_mock, tts_factory_mock, config_mock):
        """Ensure the fallback tts is triggered if the remote times out."""
        setup_mocks(config_mock, tts_factory_mock)
        mimic_mock = mock.Mock()
        mimic_cls_mock.return_value = mimic_mock

        tts = tts_factory_mock.create.return_value
        tts.execute.side_effect = RemoteTTSTimeoutException

        bus = mock.Mock()
        speech.init(bus)

        speak_msg = Message('speak',
                            data={'utterance': 'hello there. world',
                                  'listen': False},
                            context={'ident': 'a'})
        speech.handle_speak(speak_msg)
        mimic_mock.execute.assert_has_calls(
                [mock.call('hello there.', 'a', False),
                 mock.call('world', 'a', False)])

    @mock.patch('mycroft.audio.speech.check_for_signal')
    def test_abort_speak(self, check_for_signal_mock, tts_factory_mock,
                         config_mock):
        """Ensure the speech handler aborting speech on stop signal."""
        setup_mocks(config_mock, tts_factory_mock)
        check_for_signal_mock.return_value = True
        tts = tts_factory_mock.create.return_value

        def execute_trigger_stop():
            speech.handle_stop(None)

        tts.execute.side_effect = execute_trigger_stop

        bus = mock.Mock()
        speech.init(bus)

        speak_msg = Message('speak',
                            data={'utterance': 'hello there. world',
                                  'listen': False},
                            context={'ident': 'a'})
        speech.handle_speak(speak_msg)
        self.assertTrue(tts.playback.clear.called)

    def test_speak_picroft(self, tts_factory_mock, config_mock):
        """Ensure that picroft doesn't split the sentence."""
        setup_mocks(config_mock, tts_factory_mock)
        bus = mock.Mock()
        config_mock.get.return_value = {'enclosure': {'platform': 'picroft'}}
        speech.init(bus)

        speak_msg = Message('speak',
                            data={'utterance': 'hello there. world',
                                  'listen': False},
                            context={'ident': 'a'})
        speech.handle_speak(speak_msg)
        tts_mock.execute.assert_has_calls(
                [mock.call('hello there. world', 'a', False, None)])

        config_mock.get.return_value = {}

    def test_speak_update_tts(self, tts_factory_mock, config_mock):
        """Verify that a new config triggers reload of tts."""
        setup_mocks(config_mock, tts_factory_mock)
        bus = mock.Mock()
        config_mock.get.return_value = {'tts': {'module': 'test'}}
        speech.init(bus)
        tts_factory_mock.create.reset_mock()
        speak_msg = Message('speak',
                            data={'utterance': 'hello there. world',
                                  'listen': False},
                            context={'ident': 'a'})
        speech.handle_speak(speak_msg)
        self.assertFalse(tts_factory_mock.create.called)

        speech.config = {'tts': {'module': 'test2'}}
        speech.handle_speak(speak_msg)
        self.assertTrue(tts_factory_mock.create.called)

    @mock.patch('mycroft.audio.speech.check_for_signal')
    def test_stop(self, check_for_signal_mock, tts_factory_mock, config_mock):
        """Ensure the stop handler signals stop correctly."""
        setup_mocks(config_mock, tts_factory_mock)
        bus = mock.Mock()
        config_mock.get.return_value = {'tts': {'module': 'test'}}
        speech.init(bus)

        speech._last_stop_signal = 0
        check_for_signal_mock.return_value = False
        speech.handle_stop(Message('mycroft.stop'))
        self.assertEqual(speech._last_stop_signal, 0)

        check_for_signal_mock.return_value = True
        speech.handle_stop(Message('mycroft.stop'))
        self.assertNotEqual(speech._last_stop_signal, 0)


if __name__ == "__main__":
    unittest.main()
