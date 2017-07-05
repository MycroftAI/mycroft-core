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


import abc
import imp
import time

import os.path
import re
import time
from os.path import join, dirname, splitext, isdir

from functools import wraps

from adapt.intent import Intent

from mycroft.client.enclosure.api import EnclosureAPI
from mycroft.configuration import ConfigurationManager
from mycroft.dialog import DialogLoader
from mycroft.filesystem import FileSystemAccess
from mycroft.messagebus.message import Message
from mycroft.util.log import getLogger
from mycroft.skills.settings import SkillSettings
__author__ = 'seanfitz'

skills_config = ConfigurationManager.instance().get("skills")
BLACKLISTED_SKILLS = skills_config.get("blacklisted_skills", [])

SKILLS_DIR = "/opt/mycroft/skills"

MainModule = '__init__'

logger = getLogger(__name__)


def load_vocab_from_file(path, vocab_type, emitter):
    if path.endswith('.voc'):
        with open(path, 'r') as voc_file:
            for line in voc_file.readlines():
                parts = line.strip().split("|")
                entity = parts[0]

                emitter.emit(Message("register_vocab", {
                    'start': entity, 'end': vocab_type
                }))
                for alias in parts[1:]:
                    emitter.emit(Message("register_vocab", {
                        'start': alias, 'end': vocab_type, 'alias_of': entity
                    }))


def load_regex_from_file(path, emitter):
    if path.endswith('.rx'):
        with open(path, 'r') as reg_file:
            for line in reg_file.readlines():
                re.compile(line.strip())
                emitter.emit(
                    Message("register_vocab", {'regex': line.strip()}))


def load_vocabulary(basedir, emitter):
    for vocab_type in os.listdir(basedir):
        if vocab_type.endswith(".voc"):
            load_vocab_from_file(
                join(basedir, vocab_type), splitext(vocab_type)[0], emitter)


def load_regex(basedir, emitter):
    for regex_type in os.listdir(basedir):
        if regex_type.endswith(".rx"):
            load_regex_from_file(
                join(basedir, regex_type), emitter)


def open_intent_envelope(message):
    intent_dict = message.data
    return Intent(intent_dict.get('name'),
                  intent_dict.get('requires'),
                  intent_dict.get('at_least_one'),
                  intent_dict.get('optional'))


def load_skill(skill_descriptor, emitter):
    try:
        logger.info("ATTEMPTING TO LOAD SKILL: " + skill_descriptor["name"])
        if skill_descriptor['name'] in BLACKLISTED_SKILLS:
            logger.info("SKILL IS BLACKLISTED " + skill_descriptor["name"])
            return None
        skill_module = imp.load_module(
            skill_descriptor["name"] + MainModule, *skill_descriptor["info"])
        if (hasattr(skill_module, 'create_skill') and
                callable(skill_module.create_skill)):
            # v2 skills framework
            skill = skill_module.create_skill()
            skill.bind(emitter)
            skill._dir = dirname(skill_descriptor['info'][1])
            skill.load_data_files(dirname(skill_descriptor['info'][1]))
            # Set up intent handlers
            skill.initialize()
            skill._register_decorated()
            logger.info("Loaded " + skill_descriptor["name"])
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
    logger.info("LOADING SKILLS FROM " + skills_folder)
    skills = []
    possible_skills = os.listdir(skills_folder)
    for i in possible_skills:
        location = join(skills_folder, i)
        if (isdir(location) and
                not MainModule + ".py" in os.listdir(location)):
            for j in os.listdir(location):
                name = join(location, j)
                if (not isdir(name) or
                        not MainModule + ".py" in os.listdir(name)):
                    continue
                skills.append(create_skill_descriptor(name))
        if (not isdir(location) or
                not MainModule + ".py" in os.listdir(location)):
            continue

        skills.append(create_skill_descriptor(location))
    skills = sorted(skills, key=lambda p: p.get('name'))
    return skills


def create_skill_descriptor(skill_folder):
    info = imp.find_module(MainModule, [skill_folder])
    return {"name": os.path.basename(skill_folder), "info": info}


def load_skills(emitter, skills_root=SKILLS_DIR):
    logger.info("Checking " + skills_root + " for new skills")
    skill_list = []
    for skill in get_skills(skills_root):
        skill_list.append(load_skill(skill, emitter))

    return skill_list


def unload_skills(skills):
    for s in skills:
        s.shutdown()


_intent_list = []


def intent_handler(intent_parser):
    """ Decorator for adding a method as an intent handler. """
    def real_decorator(func):
        @wraps(func)
        def handler_method(*args, **kwargs):
            return func(*args, **kwargs)
        _intent_list.append((intent_parser, func))
        return handler_method
    return real_decorator


class MycroftSkill(object):
    """
    Abstract base class which provides common behaviour and parameters to all
    Skills implementation.
    """

    def __init__(self, name, emitter=None):
        self.name = name
        self.bind(emitter)
        self.config_core = ConfigurationManager.get()
        self.config = self.config_core.get(name)
        self.dialog_renderer = None
        self.file_system = FileSystemAccess(join('skills', name))
        self.registered_intents = []
        self.log = getLogger(name)
        self.reload_skill = True
        self.events = []

    @property
    def location(self):
        """ Get the JSON data struction holding location information. """
        # TODO: Allow Enclosure to override this for devices that
        # contain a GPS.
        return self.config_core.get('location')

    @property
    def location_pretty(self):
        """ Get a more 'human' version of the location as a string. """
        loc = self.location
        if type(loc) is dict and loc["city"]:
            return loc["city"]["name"]
        return None

    @property
    def location_timezone(self):
        """ Get the timezone code, such as 'America/Los_Angeles' """
        loc = self.location
        if type(loc) is dict and loc["timezone"]:
            return loc["timezone"]["code"]
        return None

    @property
    def lang(self):
        return self.config_core.get('lang')

    @property
    def settings(self):
        """ Load settings if not already loaded. """
        try:
            return self._settings
        except:
            self._settings = SkillSettings(join(self._dir, 'settings.json'))
            return self._settings

    def bind(self, emitter):
        if emitter:
            self.emitter = emitter
            self.enclosure = EnclosureAPI(emitter)
            self.__register_stop()

    def __register_stop(self):
        self.stop_time = time.time()
        self.stop_threshold = self.config_core.get("skills").get(
            'stop_threshold')
        self.emitter.on('mycroft.stop', self.__handle_stop)

    def detach(self):
        for (name, intent) in self.registered_intents:
            name = self.name + ':' + name
            self.emitter.emit(Message("detach_intent", {"intent_name": name}))

    def initialize(self):
        """
        Initialization function to be implemented by all Skills.

        Usually used to create intents rules and register them.
        """
        logger.debug("No initialize function implemented")

    def _register_decorated(self):
        """
        Register all intent handlers that has been decorated with an intent.
        """
        global _intent_list
        for intent_parser, handler in _intent_list:
            self.register_intent(intent_parser, handler, need_self=True)
        _intent_list = []

    def register_intent(self, intent_parser, handler, need_self=False):
        name = intent_parser.name
        intent_parser.name = self.name + ':' + intent_parser.name
        self.emitter.emit(Message("register_intent", intent_parser.__dict__))
        self.registered_intents.append((name, intent_parser))

        def receive_handler(message):
            try:
                if need_self:
                    # When registring from decorator self is required
                    handler(self, message)
                else:
                    handler(message)
            except:
                # TODO: Localize
                self.speak(
                    "An error occurred while processing a request in " +
                    self.name)
                logger.error(
                    "An error occurred while processing a request in " +
                    self.name, exc_info=True)

        if handler:
            self.emitter.on(intent_parser.name, receive_handler)
            self.events.append((intent_parser.name, receive_handler))

    def disable_intent(self, intent_name):
        """Disable a registered intent"""
        logger.debug('Disabling intent ' + intent_name)
        name = self.name + ':' + intent_name
        self.emitter.emit(Message("detach_intent", {"intent_name": name}))

    def enable_intent(self, intent_name):
        """Reenable a registered intent"""
        for (name, intent) in self.registered_intents:
            if name == intent_name:
                self.registered_intents.remove((name, intent))
                intent.name = name
                self.register_intent(intent, None)
                logger.debug('Enabling intent ' + intent_name)
                break
            else:
                logger.error('Could not enable ' + intent_name +
                             ', it hasn\'t been registered.')

    def register_vocabulary(self, entity, entity_type):
        self.emitter.emit(Message('register_vocab', {
            'start': entity, 'end': entity_type
        }))

    def register_regex(self, regex_str):
        re.compile(regex_str)  # validate regex
        self.emitter.emit(Message('register_vocab', {'regex': regex_str}))

    def speak(self, utterance, expect_response=False):
        data = {'utterance': utterance,
                'expect_response': expect_response}
        self.emitter.emit(Message("speak", data))

    def speak_dialog(self, key, data={}, expect_response=False):
        data['expect_response'] = expect_response
        self.speak(self.dialog_renderer.render(key, data))

    def init_dialog(self, root_directory):
        dialog_dir = join(root_directory, 'dialog', self.lang)
        if os.path.exists(dialog_dir):
            self.dialog_renderer = DialogLoader().load(dialog_dir)
        else:
            logger.debug('No dialog loaded, ' + dialog_dir + ' does not exist')

    def load_data_files(self, root_directory):
        self.init_dialog(root_directory)
        self.load_vocab_files(join(root_directory, 'vocab', self.lang))
        regex_path = join(root_directory, 'regex', self.lang)
        if os.path.exists(regex_path):
            self.load_regex_files(regex_path)

    def load_vocab_files(self, vocab_dir):
        if os.path.exists(vocab_dir):
            load_vocabulary(vocab_dir, self.emitter)
        else:
            logger.debug('No vocab loaded, ' + vocab_dir + ' does not exist')

    def load_regex_files(self, regex_dir):
        load_regex(regex_dir, self.emitter)

    def __handle_stop(self, event):
        self.stop_time = time.time()
        self.stop()

    @abc.abstractmethod
    def stop(self):
        pass

    def is_stop(self):
        passed_time = time.time() - self.stop_time
        return passed_time < self.stop_threshold

    def shutdown(self):
        """
        This method is intended to be called during the skill
        process termination. The skill implementation must
        shutdown all processes and operations in execution.
        """
        # Store settings
        self.settings.store()

        # removing events
        for e, f in self.events:
            self.emitter.remove(e, f)

        self.emitter.emit(
            Message("detach_skill", {"skill_name": self.name + ":"}))
        self.stop()
