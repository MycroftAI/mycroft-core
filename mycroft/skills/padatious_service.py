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
from subprocess import call
from threading import Event
from time import time as get_time, sleep

from os.path import expanduser, isfile
from pkg_resources import get_distribution

from mycroft.configuration import Configuration
from mycroft.messagebus.message import Message
from mycroft.skills.core import FallbackSkill
from mycroft.util.log import LOG


PADATIOUS_VERSION = '0.3.7'  # Also update in requirements.txt


class PadatiousService(FallbackSkill):
    def __init__(self, emitter, service):
        FallbackSkill.__init__(self)
        self.config = Configuration.get()['padatious']
        self.service = service
        intent_cache = expanduser(self.config['intent_cache'])

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
        ver = get_distribution('padatious').version
        if ver != PADATIOUS_VERSION:
            LOG.warning('Using Padatious v' + ver + '. Please re-run ' +
                        'dev_setup.sh to install ' + PADATIOUS_VERSION)

        self.container = IntentContainer(intent_cache)

        self.emitter = emitter
        self.emitter.on('padatious:register_intent', self.register_intent)
        self.emitter.on('padatious:register_entity', self.register_entity)
        self.emitter.on('mycroft.skills.initialized', self.train)
        self.register_fallback(self.handle_fallback, 5)
        self.finished_training_event = Event()
        self.finished_initial_train = False

        self.train_delay = self.config['train_delay']
        self.train_time = get_time() + self.train_delay

    def train(self, message=None):
        self.finished_training_event.clear()
        LOG.info('Training...')
        self.container.train()
        LOG.info('Training complete.')
        self.finished_training_event.set()
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
        self._register_object(message, 'intent', self.container.load_intent)

    def register_entity(self, message):
        self._register_object(message, 'entity', self.container.load_entity)

    def handle_fallback(self, message):
        utt = message.data.get('utterance')
        LOG.debug("Padatious fallback attempt: " + utt)

        if not self.finished_training_event.is_set():
            LOG.debug('Waiting for training to finish...')
            self.finished_training_event.wait()

        data = self.container.calc_intent(utt)

        if data.conf < 0.5:
            return False

        data.matches['utterance'] = utt

        self.service.add_active_skill(int(data.name.split(':')[0]))

        self.emitter.emit(Message(data.name, data=data.matches))
        return True
