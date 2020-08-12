# Copyright 2020 Mycroft AI Inc.
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
"""Intent service wrapping padatious."""
from functools import lru_cache
from subprocess import call
from threading import Event
from time import time as get_time, sleep

from os.path import expanduser, isfile

from mycroft.configuration import Configuration
from mycroft.messagebus.message import Message
from mycroft.util.log import LOG
from .base import IntentMatch


class PadatiousService:
    """Service class for padatious intent matching."""
    def __init__(self, bus, config):
        self.padatious_config = config
        self.bus = bus
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

        self.finished_training_event = Event()
        self.finished_initial_train = False

        self.train_delay = self.padatious_config['train_delay']
        self.train_time = get_time() + self.train_delay

        self.registered_intents = []
        self.registered_entities = []

    def train(self, message=None):
        """Perform padatious training.

        Arguments:
            message (Message): optional triggering message
        """
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
        """Wait for minimum time between training and start training."""
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
        """Messagebus handler for detaching padatious intent.

        Arguments:
            message (Message): message triggering action
        """
        self.__detach_intent(message.data.get('intent_name'))

    def handle_detach_skill(self, message):
        """Messagebus handler for detaching all intents for skill.

        Arguments:
            message (Message): message triggering action
        """
        skill_id = message.data['skill_id']
        remove_list = [i for i in self.registered_intents if skill_id in i]
        for i in remove_list:
            self.__detach_intent(i)

    def _register_object(self, message, object_name, register_func):
        """Generic method for registering a padatious object.

        Arguments:
            message (Message): trigger for action
            object_name (str): type of entry to register
            register_func (callable): function to call for registration
        """
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
        """Messagebus handler for registering intents.

        Arguments:
            message (Message): message triggering action
        """
        self.registered_intents.append(message.data['name'])
        self._register_object(message, 'intent', self.container.load_intent)

    def register_entity(self, message):
        """Messagebus handler for registering entities.

        Arguments:
            message (Message): message triggering action
        """
        self.registered_entities.append(message.data)
        self._register_object(message, 'entity', self.container.load_entity)

    def _match_level(self, utterances, limit):
        """Match intent and make sure a certain level of confidence is reached.

        Arguments:
            utterances (list of tuples): Utterances to parse, originals paired
                                         with optional normalized version.
            limit (float): required confidence level.
        """
        padatious_intent = None
        LOG.debug('Padatious Matching confidence > {}'.format(limit))
        for utt in utterances:
            for variant in utt:
                intent = self.calc_intent(variant)
                if intent:
                    best = padatious_intent.conf if padatious_intent else 0.0
                    if best < intent.conf:
                        padatious_intent = intent
                        padatious_intent.matches['utterance'] = utt[0]

        if padatious_intent and padatious_intent.conf > limit:
            skill_id = padatious_intent.name.split(':')[0]
            ret = IntentMatch(
                'Padatious', padatious_intent.name, padatious_intent.matches,
                skill_id
            )
        else:
            ret = None
        return ret

    def match_high(self, utterances, _=None, __=None):
        """Intent matcher for high confidence.

        Arguments:
            utterances (list of tuples): Utterances to parse, originals paired
                                         with optional normalized version.
        """
        return self._match_level(utterances, 0.95)

    def match_medium(self, utterances, _=None, __=None):
        """Intent matcher for medium confidence.

        Arguments:
            utterances (list of tuples): Utterances to parse, originals paired
                                         with optional normalized version.
        """
        return self._match_level(utterances, 0.8)

    def match_low(self, utterances, _=None, __=None):
        """Intent matcher for low confidence.

        Arguments:
            utterances (list of tuples): Utterances to parse, originals paired
                                         with optional normalized version.
        """
        return self._match_level(utterances, 0.5)

    def handle_get_padatious(self, message):
        """messagebus handler for perfoming padatious parsing.

        Arguments:
            message (Message): message triggering the method
        """
        utterance = message.data["utterance"]
        norm = message.data.get('norm_utt', utterance)
        intent = self.calc_intent(utterance)
        if not intent and norm != utterance:
            intent = self.calc_intent(norm)
        if intent:
            intent = intent.__dict__
        self.bus.emit(message.reply("intent.service.padatious.reply",
                                    {"intent": intent}))

    def handle_manifest(self, message):
        """Messagebus handler returning the registered padatious intents.

        Arguments:
            message (Message): message triggering the method
        """
        self.bus.emit(message.reply("intent.service.padatious.manifest",
                                    {"intents": self.registered_intents}))

    def handle_entity_manifest(self, message):
        """Messagebus handler returning the registered padatious entities.

        Arguments:
            message (Message): message triggering the method
        """
        self.bus.emit(
            message.reply("intent.service.padatious.entities.manifest",
                          {"entities": self.registered_entities}))

    @lru_cache(maxsize=2)  # 2 catches both raw and normalized utts in cache
    def calc_intent(self, utt):
        """Cached version of container calc_intent.

        This improves speed when called multiple times for different confidence
        levels.

        NOTE: This cache will keep a reference to this class
        (PadatiousService), but we can live with that since it is used as a
        singleton.

        Arguments:
            utt (str): utterance to calculate best intent for
        """
        return self.container.calc_intent(utt)
