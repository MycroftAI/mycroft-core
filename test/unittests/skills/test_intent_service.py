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
from threading import Thread
import time
from unittest import TestCase, mock

from mycroft.messagebus import Message
from mycroft.skills.intent_service import ContextManager, IntentService


class MockEmitter(object):
    def __init__(self):
        self.reset()

    def emit(self, message):
        self.types.append(message.msg_type)
        self.results.append(message.data)

    def get_types(self):
        return self.types

    def get_results(self):
        return self.results

    def reset(self):
        self.types = []
        self.results = []


class ContextManagerTest(TestCase):
    emitter = MockEmitter()

    def setUp(self):
        self.context_manager = ContextManager(3)

    def test_add_context(self):
        entity = {'confidence': 1.0}
        context = 'TestContext'
        word = 'TestWord'
        entity['data'] = [(word, context)]
        entity['match'] = word
        entity['key'] = word

        self.assertEqual(len(self.context_manager.frame_stack), 0)
        self.context_manager.inject_context(entity)
        self.assertEqual(len(self.context_manager.frame_stack), 1)

    def test_remove_context(self):
        entity = {'confidence': 1.0}
        context = 'TestContext'
        word = 'TestWord'
        entity['data'] = [(word, context)]
        entity['match'] = word
        entity['key'] = word

        self.context_manager.inject_context(entity)
        self.assertEqual(len(self.context_manager.frame_stack), 1)
        self.context_manager.remove_context('TestContext')
        self.assertEqual(len(self.context_manager.frame_stack), 0)


def check_converse_request(message, skill_id):
    return (message.msg_type == 'skill.converse.request' and
            message.data['skill_id'] == skill_id)


class ConversationTest(TestCase):
    def setUp(self):
        bus = mock.Mock()
        self.intent_service = IntentService(bus)
        self.intent_service.add_active_skill('atari_skill')
        self.intent_service.add_active_skill('c64_skill')

    def test_converse(self):
        """Check that the _converse method reports if the utterance is handled.

        Also check that the skill that handled the query is moved to the
        top of the active skill list.
        """
        result = None

        def runner(utterances, lang, message):
            nonlocal result
            result = self.intent_service._converse(utterances, lang, message)

        hello = ['hello old friend']
        utterance_msg = Message('recognizer_loop:utterance',
                                data={'lang': 'en-US',
                                      'utterances': hello})
        t = Thread(target=runner, args=(hello, 'en-US', utterance_msg))
        t.start()
        time.sleep(0.5)
        self.intent_service.handle_converse_response(
            Message('converse.response', {'skill_id': 'c64_skill',
                                          'result': False}))
        time.sleep(0.5)
        self.intent_service.handle_converse_response(
            Message('converse.response', {'skill_id': 'atari_skill',
                                          'result': True}))
        t.join()

        # Check that the active skill list was updated to set the responding
        # Skill first.
        first_active_skill = self.intent_service.active_skills[0][0]
        self.assertEqual(first_active_skill, 'atari_skill')

        # Check that a skill responded that it could handle the message
        self.assertTrue(result)

    def test_reset_converse(self):
        """Check that a blank stt sends the reset signal to the skills."""
        print(self.intent_service.active_skills)
        reset_msg = Message('mycroft.speech.recognition.unknown',
                            data={'lang': 'en-US'})
        t = Thread(target=self.intent_service.reset_converse,
                   args=(reset_msg,))
        t.start()
        time.sleep(0.5)
        self.intent_service.handle_converse_error(
            Message('converse.error', {'skill_id': 'c64_skill',
                                       'error': 'skill id does not exist'}))
        time.sleep(0.5)
        self.intent_service.handle_converse_response(
            Message('converse.response', {'skill_id': 'atari_skill',
                                          'result': False}))

        # Check send messages
        c64_message = self.intent_service.bus.emit.call_args_list[0][0][0]
        self.assertTrue(check_converse_request(c64_message, 'c64_skill'))
        atari_message = self.intent_service.bus.emit.call_args_list[1][0][0]
        self.assertTrue(check_converse_request(atari_message, 'atari_skill'))
