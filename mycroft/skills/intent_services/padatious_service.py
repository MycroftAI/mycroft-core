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

from os import path
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
        self.lang = Configuration.get().get('lang', 'en-us')
        self.supported_langs = Configuration.get().get('supported_langs', [
            self.lang])
        if self.lang not in self.supported_langs:
            self.supported_langs.append(self.lang)
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

        self.containers = {lang: IntentContainer(path.join(intent_cache, lang))
                           for lang in self.supported_langs}

        self._bus = bus
        self.bus.on('padatious:register_intent', self.register_intent)
        self.bus.on('padatious:register_entity', self.register_entity)
        self.bus.on('detach_intent', self.handle_detach_intent)
        self.bus.on('detach_skill', self.handle_detach_skill)
        self.bus.on('mycroft.skills.initialized', self.train)

        self.finished_training_event = Event()
        self.finished_initial_train = False

        self.train_delay = self.padatious_config['train_delay']
        self.train_time = get_time() + self.train_delay

        self.registered_intents = []
        self.registered_entities = []

    def train(self, message=None):
        """Perform padatious training.

        Args:
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
        for lang in self.supported_langs:
            self.containers[lang].train(single_thread=single_thread)
        LOG.info('Training complete.')

        self.finished_training_event.set()
        if not self.finished_initial_train:
            self.bus.emit(Message('mycroft.skills.trained'))
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

        Args:
            intent_name (str): intent identifier
        """
        if intent_name in self.registered_intents:
            self.registered_intents.remove(intent_name)
            for lang in self.supported_langs:
                self.containers[lang].remove_intent(intent_name)

    def handle_detach_intent(self, message):
        """Messagebus handler for detaching padatious intent.

        Args:
            message (Message): message triggering action
        """
        self.__detach_intent(message.data.get('intent_name'))

    def handle_detach_skill(self, message):
        """Messagebus handler for detaching all intents for skill.

        Args:
            message (Message): message triggering action
        """
        skill_id = message.data['skill_id']
        remove_list = [i for i in self.registered_intents if skill_id in i]
        for i in remove_list:
            self.__detach_intent(i)

    def get_file_lang(self, file_name):
        _path, _ = path.split(file_name)
        _, _name = path.split(_path)
        return _name

    def _register_object(self, message, object_name, register_func):
        """Generic method for registering a padatious object.

        Args:
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

        Args:
            message (Message): message triggering action
        """
        lang = self.get_file_lang(message.data['file_name'])
        if lang in self.supported_langs:
            if message.data['name'] not in self.registered_intents:
                self.registered_intents.append(message.data['name'])
            self._register_object(
                message, 'intent', self.containers[lang].load_intent)

    def register_entity(self, message):
        """Messagebus handler for registering entities.

        Args:
            message (Message): message triggering action
        """
        lang = self.get_file_lang(message.data['file_name'])
        if lang in self.supported_langs:
            self.registered_entities.append(message.data)
            self._register_object(
                message, 'entity', self.containers[lang].load_entity)

    def _match_level(self, utterances, limit, lang=None):
        """Match intent and make sure a certain level of confidence is reached.

        Args:
            utterances (list of tuples): Utterances to parse, originals paired
                                         with optional normalized version.
            limit (float): required confidence level.
        """
        lang = lang or self.lang
        padatious_intent = None
        LOG.debug('Padatious Matching confidence > {}'.format(limit))
        for utt in utterances:
            for variant in utt:
                intent = self.calc_intent(variant, lang)
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

    def match_high(self, utterances, lang=None, __=None):
        """Intent matcher for high confidence.

        Args:
            utterances (list of tuples): Utterances to parse, originals paired
                                         with optional normalized version.
        """
        return self._match_level(utterances, 0.95, lang=lang)

    def match_medium(self, utterances, lang=None, __=None):
        """Intent matcher for medium confidence.

        Args:
            utterances (list of tuples): Utterances to parse, originals paired
                                         with optional normalized version.
        """
        return self._match_level(utterances, 0.8, lang=lang)

    def match_low(self, utterances, lang=None, __=None):
        """Intent matcher for low confidence.

        Args:
            utterances (list of tuples): Utterances to parse, originals paired
                                         with optional normalized version.
        """
        return self._match_level(utterances, 0.5, lang=lang)

    @lru_cache(maxsize=2)  # 2 catches both raw and normalized utts in cache
    def calc_intent(self, utt, lang=None):
        """Cached version of container calc_intent.

        This improves speed when called multiple times for different confidence
        levels.

        NOTE: This cache will keep a reference to this class
        (PadatiousService), but we can live with that since it is used as a
        singleton.

        Args:
            utt (str): utterance to calculate best intent for
        """
        lang = lang or self.lang
        if lang in self.supported_langs:
            return self.containers[lang].calc_intent(utt)
