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
from time import time as get_time, sleep

from threading import Event
from os.path import expanduser, isfile

from mycroft.configuration import ConfigurationManager
from mycroft.messagebus.message import Message
from mycroft.skills.core import FallbackSkill
from mycroft.util.log import getLogger
from mycroft.util.parse import normalize

__author__ = 'matthewscholefield'

logger = getLogger(__name__)


class PadatiousService(object):
    def __init__(self, emitter):
        self.config = ConfigurationManager.get()['padatious']
        intent_cache = expanduser(self.config['intent_cache'])

        try:
            from padatious import IntentContainer
        except ImportError:
            logger.error('Padatious not installed. Please re-run dev_setup.sh')
            try:
                call(['notify-send', 'Padatious not installed',
                      'Please run build_host_setup and dev_setup again'])
            except OSError:
                pass
            return

        self.container = IntentContainer(intent_cache)

        self.train_delay = self.config['train_delay']
        self.train_time = -1.0



        self.emitter = emitter
        self.emitter.on('padatious:register_intent', self.register_intent)
        FallbackSkill.register_fallback(self.handle_fallback, 5)
        self.finished_training_event = Event()

    def wait_and_train(self):
        sleep(self.train_delay)
        if self.train_time < 0.0:
            return

        if self.train_time <= get_time() + 0.01:
            self.train_time = -1.0

            self.finished_training_event.clear()
            logger.info('Training...')
            self.container.train(print_updates=False)
            logger.info('Training complete.')
            self.finished_training_event.set()

    def register_intent(self, message):
        logger.debug('Registering Padatious intent: ' +
                     message.data['intent_name'])

        file_name = message.data['file_name']
        intent_name = message.data['intent_name']
        if not isfile(file_name):
            return

        self.container.load_file(intent_name, file_name)
        self.train_time = get_time() + self.train_delay
        self.wait_and_train()

    def handle_fallback(self, message):
        utt = message.data.get('utterance')
        logger.debug("Padatious fallback attempt: " + utt)

        utt = normalize(utt, message.data.get('lang', 'en-us'))

        if not self.finished_training_event.is_set():
            logger.debug('Waiting for training to finish...')
            self.finished_training_event.wait()

        data = self.container.calc_intent(utt)

        if data.conf < 0.5:
            return False

        self.emitter.emit(Message(data.name, data=data.matches))
        return True
