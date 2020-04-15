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
from functools import lru_cache
from subprocess import call
from threading import Event
from time import time as get_time, sleep

from os.path import expanduser, isfile

from mycroft.configuration import Configuration
from mycroft.messagebus.message import Message
from mycroft.skills.core import FallbackSkill
from mycroft.util.log import LOG


class PadatiousService(FallbackSkill):
    instance = None

    fallback_tight_match = 5  # Fallback priority for the conf > 0.8 match
    fallback_loose_match = 89  # Fallback priority for the conf > 0.5 match

    def __init__(self, bus, service):
        FallbackSkill.__init__(self, use_settings=False)
        if not PadatiousService.instance:
            PadatiousService.instance = self

        self.padatious_config = Configuration.get()['padatious']
        self.service = service
        intent_cache = expanduser(self.padatious_config['intent_cache'])

        try:
            from padatious import IntentContainer
        except ImportError:
            LOG.error('Padatious not installed. Please re-run dev_setup.sh')
            try:
                call(['notify-send', 'Padatious not installed',
                      'Please run build_host_setup and dev_setup again'])
            except OSError:
                pass
            return

        self.container = IntentContainer(intent_cache)

        self._bus = bus
        self.bus.on('padatious:register_intent', self.register_intent)
        self.bus.on('padatious:register_entity', self.register_entity)
        self.bus.on('detach_intent', self.handle_detach_intent)
        self.bus.on('detach_skill', self.handle_detach_skill)
        self.bus.on('mycroft.skills.initialized', self.train)
        self.bus.on('intent.service.padatious.get', self.handle_get_padatious)
        self.bus.on('intent.service.padatious.manifest.get',
                    self.handle_manifest)
        self.bus.on('intent.service.padatious.entities.manifest.get',
                    self.handle_entity_manifest)

        # Call Padatious an an early fallback, looking for a high match intent
        self.register_fallback(self.handle_fallback,
                               PadatiousService.fallback_tight_match)

        # Try loose Padatious intent match before going to fallback-unknown
        self.register_fallback(self.handle_fallback_last_chance,
                               PadatiousService.fallback_loose_match)

        self.finished_training_event = Event()
        self.finished_initial_train = False

        self.train_delay = self.padatious_config['train_delay']
        self.train_time = get_time() + self.train_delay

        self.registered_intents = []
        self.registered_entities = []

    def make_active(self):
        """Override the make active since this is not a real fallback skill."""
        pass

    def train(self, message=None):
        padatious_single_thread = Configuration.get()[
            'padatious']['single_thread']
        if message is None:
            single_thread = padatious_single_thread
        else:
            single_thread = message.data.get('single_thread',
                                             padatious_single_thread)

        self.finished_training_event.clear()

        LOG.info('Training... (single_thread={})'.format(single_thread))
        self.container.train(single_thread=single_thread)
        LOG.info('Training complete.')

        self.finished_training_event.set()
        if not self.finished_initial_train:
            LOG.info("Mycroft is all loaded and ready to roll!")
            self.bus.emit(Message('mycroft.ready'))
            self.finished_initial_train = True

    def wait_and_train(self):
        if not self.finished_initial_train:
            return
        sleep(self.train_delay)
        if self.train_time < 0.0:
            return

        if self.train_time <= get_time() + 0.01:
            self.train_time = -1.0
            self.train()

    def __detach_intent(self, intent_name):
        """ Remove an intent if it has been registered.

        Arguments:
            intent_name (str): intent identifier
        """
        if intent_name in self.registered_intents:
            self.registered_intents.remove(intent_name)
            self.container.remove_intent(intent_name)

    def handle_detach_intent(self, message):
        self.__detach_intent(message.data.get('intent_name'))

    def handle_detach_skill(self, message):
        skill_id = message.data['skill_id']
        remove_list = [i for i in self.registered_intents if skill_id in i]
        for i in remove_list:
            self.__detach_intent(i)

    def _register_object(self, message, object_name, register_func):
        file_name = message.data['file_name']
        name = message.data['name']

        LOG.debug('Registering Padatious ' + object_name + ': ' + name)

        if not isfile(file_name):
            LOG.warning('Could not find file ' + file_name)
            return

        register_func(name, file_name)
        self.train_time = get_time() + self.train_delay
        self.wait_and_train()

    def register_intent(self, message):
        self.registered_intents.append(message.data['name'])
        self._register_object(message, 'intent', self.container.load_intent)

    def register_entity(self, message):
        self.registered_entities.append(message.data)
        self._register_object(message, 'entity', self.container.load_entity)

    def handle_fallback(self, message, threshold=0.8):
        if not self.finished_training_event.is_set():
            LOG.debug('Waiting for Padatious training to finish...')
            return False

        utt = message.data.get('utterance', '')
        LOG.debug("Padatious fallback attempt: " + utt)
        intent = self.calc_intent(utt)

        if not intent or intent.conf < threshold:
            # Attempt to use normalized() version
            norm = message.data.get('norm_utt', utt)
            if norm != utt:
                LOG.debug("               alt attempt: " + norm)
                intent = self.calc_intent(norm)
                utt = norm
        if not intent or intent.conf < threshold:
            return False

        intent.matches['utterance'] = utt
        self.service.add_active_skill(intent.name.split(':')[0])
        self.bus.emit(message.forward(intent.name, data=intent.matches))
        return True

    def handle_fallback_last_chance(self, message):
        return self.handle_fallback(message, 0.5)

    def handle_get_padatious(self, message):
        utterance = message.data["utterance"]
        norm = message.data.get('norm_utt', utterance)
        intent = self.calc_intent(utterance)
        if not intent and norm != utterance:
            intent = PadatiousService.instance.calc_intent(norm)
        if intent:
            intent = intent.__dict__
        self.bus.emit(message.reply("intent.service.padatious.reply",
                                    {"intent": intent}))

    def handle_manifest(self, message):
        self.bus.emit(message.reply("intent.service.padatious.manifest",
                                    {"intents": self.registered_intents}))

    def handle_entity_manifest(self, message):
        self.bus.emit(
            message.reply("intent.service.padatious.entities.manifest",
                          {"entities": self.registered_entities}))

    # NOTE: This cache will keep a reference to this calss (PadatiousService),
    # but we can live with that since it is used as a singleton.
    @lru_cache(maxsize=2)  # 2 catches both raw and normalized utts in cache
    def calc_intent(self, utt):
        return self.container.calc_intent(utt)
