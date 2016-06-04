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


import imp
import time

import abc
import os.path
import re
from adapt.intent import Intent
from os.path import join, dirname, splitext, isdir

from mycroft.client.enclosure.api import EnclosureAPI
from mycroft.configuration.config import ConfigurationManager
from mycroft.dialog import DialogLoader
from mycroft.filesystem import FileSystemAccess
from mycroft.messagebus.message import Message
from mycroft.util.log import getLogger

__author__ = 'seanfitz'

PRIMARY_SKILLS = ['intent', 'wake']
BLACKLISTED_SKILLS = ["send_sms"]
SKILLS_BASEDIR = dirname(__file__)

MainModule = '__init__'

logger = getLogger(__name__)


def load_vocab_from_file(path, vocab_type, emitter):
    with open(path, 'r') as voc_file:
        for line in voc_file.readlines():
            parts = line.strip().split("|")
            entity = parts[0]

            emitter.emit(
                Message("register_vocab",
                        metadata={'start': entity, 'end': vocab_type}))
            for alias in parts[1:]:
                emitter.emit(
                    Message("register_vocab",
                            metadata={'start': alias, 'end': vocab_type,
                                      'alias_of': entity}))


def load_vocabulary(basedir, emitter):
    for vocab_type in os.listdir(basedir):
        load_vocab_from_file(
            join(basedir, vocab_type), splitext(vocab_type)[0], emitter)


def create_intent_envelope(intent):
    return Message(None, metadata=intent.__dict__, context={})


def open_intent_envelope(message):
    intent_dict = message.metadata
    return Intent(intent_dict.get('name'),
                  intent_dict.get('requires'),
                  intent_dict.get('at_least_one'),
                  intent_dict.get('optional'))


def load_skill(skill_descriptor, emitter):
    try:
        skill_module = imp.load_module(
            skill_descriptor["name"] + MainModule, *skill_descriptor["info"])
        if (hasattr(skill_module, 'create_skill') and
                callable(skill_module.create_skill)):
            # v2 skills framework
            skill = skill_module.create_skill()
            skill.bind(emitter)
            skill.initialize()
            return skill
        else:
            logger.warn(
                "Module %s does not appear to be skill" % (
                    skill_descriptor["name"]))
    except:
        logger.error(
            "Failed to load skill: " + skill_descriptor["name"], exc_info=True)
    return None


def get_skills(skills_folder):
    skills = []
    possible_skills = os.listdir(skills_folder)
    for i in possible_skills:
        location = join(skills_folder, i)
        if (not isdir(location) or
                not MainModule + ".py" in os.listdir(location)):
            continue

        skills.append(create_skill_descriptor(location))
    skills = sorted(skills, key=lambda p: p.get('name'))
    return skills


def create_skill_descriptor(skill_folder):
    info = imp.find_module(MainModule, [skill_folder])
    return {"name": os.path.basename(skill_folder), "info": info}


def load_skills(emitter, skills_root=SKILLS_BASEDIR):
    skills = get_skills(skills_root)
    for skill in skills:
        if skill['name'] in PRIMARY_SKILLS:
            load_skill(skill, emitter)

    for skill in skills:
        if (skill['name'] not in PRIMARY_SKILLS and
                skill['name'] not in BLACKLISTED_SKILLS):
            load_skill(skill, emitter)


class MycroftSkill(object):
    """
    Abstract base class which provides common behaviour and parameters to all
    Skills implementation.
    """

    def __init__(self, name, emitter=None):
        self.name = name
        self.bind(emitter)
        config = ConfigurationManager.get()
        self.config = config.get(name)
        self.config_core = config.get('core')
        self.dialog_renderer = None
        self.file_system = FileSystemAccess(join('skills', name))
        self.registered_intents = []

    @property
    def location(self):
        return self.config_core.get('location')

    @property
    def lang(self):
        return self.config_core.get('lang')

    def bind(self, emitter):
        if emitter:
            self.emitter = emitter
            self.enclosure = EnclosureAPI(emitter)
            self.__register_stop()

    def __register_stop(self):
        self.stop_time = time.time()
        self.stop_threshold = self.config_core.get('stop_threshold')
        self.emitter.on('mycroft.stop', self.__handle_stop)

    def detach(self):
        for name in self.registered_intents:
            self.emitter.emit(
                Message("detach_intent", metadata={"intent_name": name}))

    def initialize(self):
        """
        Initialization function to be implemented by all Skills.

        Usually used to create intents rules and register them.
        """
        raise Exception("Initialize not implemented for skill: " + self.name)

    def register_intent(self, intent_parser, handler):
        intent_message = create_intent_envelope(intent_parser)
        intent_message.message_type = "register_intent"
        self.emitter.emit(intent_message)
        self.registered_intents.append(intent_parser.name)

        def receive_handler(message):
            try:
                handler(message)
            except:
                # TODO: Localize
                self.speak(
                    "An error occurred while processing a request in " +
                    self.name)
                logger.error(
                    "An error occurred while processing a request in " +
                    self.name, exc_info=True)

        self.emitter.on(intent_parser.name, receive_handler)

    def register_vocabulary(self, entity, entity_type):
        self.emitter.emit(
            Message('register_vocab',
                    metadata={'start': entity, 'end': entity_type}))

    def register_regex(self, regex_str):
        re.compile(regex_str)  # validate regex
        self.emitter.emit(
            Message('register_vocab', metadata={'regex': regex_str}))

    def speak(self, utterance):
        self.emitter.emit(Message("speak", metadata={'utterance': utterance}))

    def speak_dialog(self, key, data={}):
        self.speak(self.dialog_renderer.render(key, data))

    def init_dialog(self, root_directory):
        self.dialog_renderer = DialogLoader().load(
            join(root_directory, 'dialog', self.lang))

    def load_data_files(self, root_directory):
        self.init_dialog(root_directory)
        self.load_vocab_files(join(root_directory, 'vocab', self.lang))

    def load_vocab_files(self, vocab_dir):
        load_vocabulary(vocab_dir, self.emitter)

    def __handle_stop(self, event):
        self.stop_time = time.time()
        self.stop()

    @abc.abstractmethod
    def stop(self):
        pass

    def is_stop(self):
        passed_time = time.time() - self.stop_time
        return passed_time < self.stop_threshold
