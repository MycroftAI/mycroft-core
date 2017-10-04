# Copyright 2017 Mycroft AI, Inc.
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
from subprocess import call
from threading import Event
from time import time as get_time, sleep

from os.path import expanduser, isfile
from pkg_resources import get_distribution

from mycroft.configuration import ConfigurationManager
from mycroft.messagebus.message import Message
from mycroft.skills.core import FallbackSkill
from mycroft.util.log import LOG

__author__ = 'matthewscholefield'


PADATIOUS_VERSION = '0.3.2'  # Also update in requirements.txt


class PadatiousService(FallbackSkill):
    def __init__(self, emitter):
        FallbackSkill.__init__(self)
        self.config = ConfigurationManager.get()['padatious']
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
        self.register_fallback(self.handle_fallback, 5)
        self.finished_training_event = Event()

        self.train_delay = self.config['train_delay']
        self.train_time = get_time() + self.train_delay
        self.wait_and_train()

    def wait_and_train(self):
        sleep(self.train_delay)
        if self.train_time < 0.0:
            return

        if self.train_time <= get_time() + 0.01:
            self.train_time = -1.0

            self.finished_training_event.clear()
            LOG.info('Training...')
            self.container.train()
            LOG.info('Training complete.')
            self.finished_training_event.set()

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
        self._register_object(message, 'intent', self.container.add_intent)

    def register_entity(self, message):
        self._register_object(message, 'entity', self.container.add_entity)

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

        self.emitter.emit(Message(data.name, data=data.matches))
        return True
