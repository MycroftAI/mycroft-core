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
import imp
import operator
import sys
import time
import csv
import inspect
from inspect import getargspec
from datetime import datetime, timedelta

import abc
import re
from adapt.intent import Intent, IntentBuilder
from os.path import join, abspath, dirname, basename, exists
from threading import Event

from mycroft import dialog
from mycroft.api import DeviceApi
from mycroft.audio import wait_while_speaking
from mycroft.client.enclosure.api import EnclosureAPI
from mycroft.configuration import Configuration
from mycroft.dialog import DialogLoader
from mycroft.filesystem import FileSystemAccess
from mycroft.messagebus.message import Message
from mycroft.metrics import report_metric, report_timing, Stopwatch
from mycroft.skills.settings import SkillSettings
from mycroft.skills.skill_data import (load_vocabulary, load_regex, to_letters,
                                       munge_regex, munge_intent_parser)
from mycroft.util import resolve_resource_file
from mycroft.util.log import LOG
# python 2+3 compatibility
from past.builtins import basestring

MainModule = '__init__'


def dig_for_message():
    """
        Dig Through the stack for message.
    """
    stack = inspect.stack()
    # Limit search to 10 frames back
    stack = stack if len(stack) < 10 else stack[:10]
    local_vars = [frame[0].f_locals for frame in stack]
    for l in local_vars:
        if 'message' in l and isinstance(l['message'], Message):
            return l['message']


def unmunge_message(message, skill_id):
    """Restore message keywords by removing the Letterified skill ID.

    Args:
        message (Message): Intent result message
        skill_id (int): skill identifier

    Returns:
        Message without clear keywords
    """
    if isinstance(message, Message) and isinstance(message.data, dict):
        skill_id = to_letters(skill_id)
        for key in message.data:
            if key[:len(skill_id)] == skill_id:
                new_key = key[len(skill_id):]
                message.data[new_key] = message.data.pop(key)

    return message


def open_intent_envelope(message):
    """ Convert dictionary received over messagebus to Intent. """
    intent_dict = message.data
    return Intent(intent_dict.get('name'),
                  intent_dict.get('requires'),
                  intent_dict.get('at_least_one'),
                  intent_dict.get('optional'))


def load_skill(skill_descriptor, emitter, skill_id, BLACKLISTED_SKILLS=None):
    """
        load skill from skill descriptor.

        Args:
            skill_descriptor: descriptor of skill to load
            emitter:          messagebus emitter
            skill_id:         id number for skill
        Returns:
            MycroftSkill: the loaded skill or None on failure
    """
    BLACKLISTED_SKILLS = BLACKLISTED_SKILLS or []
    try:
        LOG.info("ATTEMPTING TO LOAD SKILL: " + skill_descriptor["name"] +
                 " with ID " + str(skill_id))
        if skill_descriptor['name'] in BLACKLISTED_SKILLS:
            LOG.info("SKILL IS BLACKLISTED " + skill_descriptor["name"])
            return None
        skill_module = imp.load_module(
            skill_descriptor["name"] + MainModule, *skill_descriptor["info"])
        if (hasattr(skill_module, 'create_skill') and
                callable(skill_module.create_skill)):
            # v2 skills framework
            skill = skill_module.create_skill()
            skill.settings.allow_overwrite = True
            skill.settings.load_skill_settings_from_file()
            skill.bind(emitter)
            skill.skill_id = skill_id
            skill.load_data_files(dirname(skill_descriptor['info'][1]))
            # Set up intent handlers
            skill.initialize()
            skill._register_decorated()
            LOG.info("Loaded " + skill_descriptor["name"])

            # The very first time a skill is run, speak the intro
            first_run = skill.settings.get("__mycroft_skill_firstrun", True)
            if first_run:
                LOG.info("First run of " + skill_descriptor["name"])
                skill.settings["__mycroft_skill_firstrun"] = False
                skill.settings.store()
                intro = skill.get_intro_message()
                if intro:
                    skill.speak(intro)
            return skill
        else:
            LOG.warning(
                "Module %s does not appear to be skill" % (
                    skill_descriptor["name"]))
    except:
        LOG.error(
            "Failed to load skill: " + skill_descriptor["name"],
            exc_info=True)
    return None


def create_skill_descriptor(skill_folder):
    info = imp.find_module(MainModule, [skill_folder])
    return {"name": basename(skill_folder), "info": info}


def get_handler_name(handler):
    """
        Return name (including class if available) of handler
        function.

        Args:
            handler (function): Function to be named

        Returns: handler name as string
    """
    name = ''
    if '__self__' in dir(handler) and 'name' in dir(handler.__self__):
        name += handler.__self__.name + '.'
    name += handler.__name__
    return name


def intent_handler(intent_parser):
    """ Decorator for adding a method as an intent handler. """

    def real_decorator(func):
        # Store the intent_parser inside the function
        # This will be used later to call register_intent
        if not hasattr(func, 'intents'):
            func.intents = []
        func.intents.append(intent_parser)
        return func

    return real_decorator


def intent_file_handler(intent_file):
    """ Decorator for adding a method as an intent file handler. """

    def real_decorator(func):
        # Store the intent_file inside the function
        # This will be used later to call register_intent_file
        if not hasattr(func, 'intent_files'):
            func.intent_files = []
        func.intent_files.append(intent_file)
        return func

    return real_decorator


#######################################################################
# MycroftSkill base class
#######################################################################
class MycroftSkill(object):
    """
    Abstract base class which provides common behaviour and parameters to all
    Skills implementation.
    """

    def __init__(self, name=None, emitter=None):
        self.name = name or self.__class__.__name__
        # Get directory of skill
        self._dir = dirname(abspath(sys.modules[self.__module__].__file__))
        self.settings = SkillSettings(self._dir, self.name)

        self.bind(emitter)
        self.config_core = Configuration.get()
        self.config = self.config_core.get(self.name) or {}
        self.dialog_renderer = None
        self.vocab_dir = None
        self.root_dir = None
        self.file_system = FileSystemAccess(join('skills', self.name))
        self.registered_intents = []
        self.log = LOG.create_logger(self.name)
        self.reload_skill = True  # allow reloading
        self.events = []
        self.scheduled_repeats = []
        self.skill_id = 0

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

    def bind(self, emitter):
        """ Register emitter with skill. """
        if emitter:
            self.emitter = emitter
            self.enclosure = EnclosureAPI(emitter, self.name)
            self.__register_stop()
            self.add_event('mycroft.skill.enable_intent',
                           self.handle_enable_intent)
            self.add_event('mycroft.skill.disable_intent',
                           self.handle_disable_intent)

            name = 'mycroft.skills.settings.update'
            func = self.settings.run_poll
            emitter.on(name, func)
            self.events.append((name, func))

    def __register_stop(self):
        self.stop_time = time.time()
        self.stop_threshold = self.config_core.get("skills").get(
            'stop_threshold')
        self.add_event('mycroft.stop', self.__handle_stop)

    def detach(self):
        for (name, intent) in self.registered_intents:
            name = str(self.skill_id) + ':' + name
            self.emitter.emit(Message("detach_intent", {"intent_name": name}))

    def initialize(self):
        """
        Invoked after the skill is fully constructed and registered with the
        system.  Use to perform any final setup needed for the skill.
        """
        pass

    def get_intro_message(self):
        """
        Get a message to speak on first load of the skill.  Useful
        for post-install setup instructions.

        Returns:
            str: message that will be spoken to the user
        """
        return None

    def converse(self, utterances, lang="en-us"):
        """
            Handle conversation. This method can be used to override the normal
            intent handler after the skill has been invoked once.

            To enable this override thise converse method and return True to
            indicate that the utterance has been handled.

            Args:
                utterances (list): The utterances from the user
                lang:       language the utterance is in

            Returns:    True if an utterance was handled, otherwise False
        """
        return False

    def __get_response(self):
        """
        Helper to get a reponse from the user

        Returns:
            str: user's response or None on a timeout
        """
        event = Event()

        def converse(utterances, lang="en-us"):
            converse.response = utterances[0] if utterances else None
            event.set()
            return True

        # install a temporary conversation handler
        self.make_active()
        converse.response = None
        default_converse = self.converse
        self.converse = converse
        event.wait(15)  # 10 for listener, 5 for SST, then timeout
        self.converse = default_converse
        return converse.response

    def get_response(self, dialog='', data=None, announcement='',
                     validator=None, on_fail=None, num_retries=-1):
        """
        Prompt user and wait for response

        The given dialog or announcement will be spoken, the immediately
        listen and return user response.  The response can optionally be
        validated.

        Example:
            color = self.get_response('ask.favorite.color')

        Args:
            dialog (str): Announcement dialog to read to the user
            data (dict): Data used to render the dialog
            announcement (str): Literal string (overrides dialog)
            validator (any): Function with following signature
                def validator(utterance):
                    return utterance != "red"
            on_fail (any): Dialog or function returning literal string
                           to speak on invalid input.  For example:
                def on_fail(utterance):
                    return "nobody likes the color red, pick another"
            num_retries (int): Times to ask user for input, -1 for infinite
                NOTE: User can not respond and timeout or say "cancel" to stop

        Returns:
            str: User's reply or None if timed out or canceled
        """
        data = data or {}

        def get_announcement():
            return announcement or self.dialog_renderer.render(dialog, data)

        if not get_announcement():
            raise ValueError('announcement or dialog message required')

        def on_fail_default(utterance):
            fail_data = data.copy()
            fail_data['utterance'] = utterance
            if on_fail:
                return self.dialog_renderer.render(on_fail, fail_data)
            else:
                return get_announcement()

        # TODO: Load with something like mycroft.dialog.get_all()
        cancel_voc = 'text/' + self.lang + '/cancel.voc'
        with open(resolve_resource_file(cancel_voc)) as f:
            cancel_words = list(filter(bool, f.read().split('\n')))

        def is_cancel(utterance):
            return utterance in cancel_words

        def validator_default(utterance):
            # accept anything except 'cancel'
            return not is_cancel(utterance)

        validator = validator or validator_default
        on_fail_fn = on_fail if callable(on_fail) else on_fail_default

        self.speak(get_announcement(), expect_response=True)
        wait_while_speaking()
        num_fails = 0
        while True:
            response = self.__get_response()

            if response is None:
                # if nothing said, prompt one more time
                num_none_fails = 1 if num_retries < 0 else num_retries
                if num_fails >= num_none_fails:
                    return None
            else:
                if validator(response):
                    return response

                # catch user saying 'cancel'
                if is_cancel(response):
                    return None

            num_fails += 1
            if 0 < num_retries < num_fails:
                return None

            line = on_fail_fn(response)
            self.speak(line, expect_response=True)

    def report_metric(self, name, data):
        """
        Report a skill metric to the Mycroft servers

        Args:
            name (str): Name of metric. Must use only letters and hyphens
            data (dict): JSON dictionary to report. Must be valid JSON
        """
        report_metric(basename(self.root_dir) + ':' + name, data)

    def send_email(self, title, body):
        """
        Send an email to the registered user's email

        Args:
            title (str): Title of email
            body  (str): HTML body of email. This supports
                         simple HTML like bold and italics
        """
        DeviceApi().send_email(title, body, basename(self.root_dir))

    def make_active(self):
        """
            Bump skill to active_skill list in intent_service
            this enables converse method to be called even without skill being
            used in last 5 minutes
        """
        self.emitter.emit(Message('active_skill_request',
                                  {"skill_id": self.skill_id}))

    def _register_decorated(self):
        """
        Register all intent handlers that have been decorated with an intent.

        Looks for all functions that have been marked by a decorator
        and read the intent data from them
        """
        for attr_name in dir(self):
            method = getattr(self, attr_name)

            if hasattr(method, 'intents'):
                for intent in getattr(method, 'intents'):
                    self.register_intent(intent, method)

            if hasattr(method, 'intent_files'):
                for intent_file in getattr(method, 'intent_files'):
                    self.register_intent_file(intent_file, method)

    def translate(self, text, data=None):
        """
        Load a translatable single string resource

        The string is loaded from a file in the skill's dialog subdirectory
          'dialog/<lang>/<text>.dialog'
        The string is randomly chosen from the file and rendered, replacing
        mustache placeholders with values found in the data dictionary.

        Args:
            text (str): The base filename  (no extension needed)
            data (dict, optional): a JSON dictionary

        Returns:
            str: A randomly chosen string from the file
        """
        return self.dialog_renderer.render(text, data or {})

    def translate_namedvalues(self, name, delim=None):
        """
        Load translation dict containing names and values.

        This loads a simple CSV from the 'dialog' folders.
        The name is the first list item, the value is the
        second.  Lines prefixed with # or // get ignored

        Args:
            name (str): name of the .value file, no extension needed
            delim (char): delimiter character used, default is ','

        Returns:
            dict: name and value dictionary, or [] if load fails
        """

        delim = delim or ','
        result = {}
        if not name.endswith(".value"):
            name += ".value"

        try:
            with open(join(self.root_dir, 'dialog', self.lang, name)) as f:
                reader = csv.reader(f, delimiter=delim)
                for row in reader:
                    # skip blank or comment lines
                    if not row or row[0].startswith("#"):
                        continue
                    if len(row) != 2:
                        continue

                    result[row[0]] = row[1]

            return result
        except Exception:
            return {}

    def translate_template(self, template_name, data=None):
        """
        Load a translatable template

        The strings are loaded from a template file in the skill's dialog
        subdirectory.
          'dialog/<lang>/<template_name>.template'
        The strings are loaded and rendered, replacing mustache placeholders
        with values found in the data dictionary.

        Args:
            template_name (str): The base filename (no extension needed)
            data (dict, optional): a JSON dictionary

        Returns:
            list of str: The loaded template file
        """
        return self.__translate_file(template_name + '.template', data)

    def translate_list(self, list_name, data=None):
        """
        Load a list of translatable string resources

        The strings are loaded from a list file in the skill's dialog
        subdirectory.
          'dialog/<lang>/<list_name>.list'
        The strings are loaded and rendered, replacing mustache placeholders
        with values found in the data dictionary.

        Args:
            list_name (str): The base filename (no extension needed)
            data (dict, optional): a JSON dictionary

        Returns:
            list of str: The loaded list of strings with items in consistent
                         positions regardless of the language.
        """
        return self.__translate_file(list_name + '.list', data)

    def __translate_file(self, name, data):
        """Load and render lines from dialog/<lang>/<name>"""
        with open(join(self.root_dir, 'dialog', self.lang, name)) as f:
            text = f.read().replace('{{', '{').replace('}}', '}')
            return text.format(**data or {}).split('\n')

    def add_event(self, name, handler, handler_info=None, once=False):
        """
            Create event handler for executing intent

            Args:
                name:           IntentParser name
                handler:        method to call
                handler_info:   base message when reporting skill event handler
                                status on messagebus.
                once:           optional parameter, Event handler will be
                                removed after it has been run once.
        """

        def wrapper(message):
            skill_data = {'name': get_handler_name(handler)}
            stopwatch = Stopwatch()
            try:
                message = unmunge_message(message, self.skill_id)
                # Indicate that the skill handler is starting
                if handler_info:
                    # Indicate that the skill handler is starting if requested
                    msg_type = handler_info + '.start'
                    self.emitter.emit(Message(msg_type, skill_data))

                with stopwatch:
                    is_bound = bool(getattr(handler, 'im_self', None))
                    num_args = len(getargspec(handler).args) - is_bound
                    if num_args == 0:
                        handler()
                    else:
                        handler(message)
                    self.settings.store()  # Store settings if they've changed

            except Exception as e:
                # Convert "MyFancySkill" to "My Fancy Skill" for speaking
                handler_name = re.sub(r"([a-z])([A-Z])", r"\1 \2", self.name)
                msg_data = {'skill': handler_name}
                msg = dialog.get('skill.error', self.lang, msg_data)
                self.speak(msg)
                LOG.exception(msg)
                # append exception information in message
                skill_data['exception'] = e.message
            finally:
                if once:
                    self.remove_event(name)

                # Indicate that the skill handler has completed
                if handler_info:
                    msg_type = handler_info + '.complete'
                    self.emitter.emit(Message(msg_type, skill_data))

                # Send timing metrics
                context = message.context
                if context and 'ident' in context:
                    report_timing(context['ident'], 'skill_handler', stopwatch,
                                  {'handler': handler.__name__})

        if handler:
            if once:
                self.emitter.once(name, wrapper)
            else:
                self.emitter.on(name, wrapper)
            self.events.append((name, wrapper))

    def remove_event(self, name):
        """
            Removes an event from emitter and events list

            Args:
                name: Name of Intent or Scheduler Event
            Returns:
                bool: True if found and removed, False if not found
        """
        removed = False
        for _name, _handler in self.events:
            if name == _name:
                try:
                    self.events.remove((_name, _handler))
                except ValueError:
                    pass
                try:
                    self.emitter.remove(_name, _handler)
                except (ValueError, KeyError):
                    LOG.debug('{} is not registered in the emitter'.format(
                              _name))
                removed = True
        return removed

    def register_intent(self, intent_parser, handler):
        """
            Register an Intent with the intent service.

            Args:
                intent_parser: Intent or IntentBuilder object to parse
                               utterance for the handler.
                handler:       function to register with intent
        """
        if type(intent_parser) == IntentBuilder:
            intent_parser = intent_parser.build()
        elif type(intent_parser) != Intent:
            raise ValueError('intent_parser is not an Intent')

        # Default to the handler's function name if none given
        name = intent_parser.name or handler.__name__
        munge_intent_parser(intent_parser, name, self.skill_id)
        self.emitter.emit(Message("register_intent", intent_parser.__dict__))
        self.registered_intents.append((name, intent_parser))
        self.add_event(intent_parser.name, handler, 'mycroft.skill.handler')

    def register_intent_file(self, intent_file, handler):
        """
            Register an Intent file with the intent service.
            For example:

            === food.order.intent ===
            Order some {food}.
            Order some {food} from {place}.
            I'm hungry.
            Grab some {food} from {place}.

            Optionally, you can also use <register_entity_file>
            to specify some examples of {food} and {place}

            In addition, instead of writing out multiple variations
            of the same sentence you can write:

            === food.order.intent ===
            (Order | Grab) some {food} (from {place} | ).
            I'm hungry.

            Args:
                intent_file: name of file that contains example queries
                             that should activate the intent
                handler:     function to register with intent
        """
        name = str(self.skill_id) + ':' + intent_file
        self.emitter.emit(Message("padatious:register_intent", {
            "file_name": join(self.vocab_dir, intent_file),
            "name": name
        }))
        self.add_event(name, handler, 'mycroft.skill.handler')

    def register_entity_file(self, entity_file):
        """
            Register an Entity file with the intent service.
            And Entity file lists the exact values that an entity can hold.
            For example:

            === ask.day.intent ===
            Is it {weekday}?

            === weekday.entity ===
            Monday
            Tuesday
            ...

            Args:
                entity_file: name of file that contains examples
                             of an entity. Must end with .entity
        """
        if '.entity' not in entity_file:
            raise ValueError('Invalid entity filename: ' + entity_file)
        name = str(self.skill_id) + ':' + entity_file.replace('.entity', '')
        self.emitter.emit(Message("padatious:register_entity", {
            "file_name": join(self.vocab_dir, entity_file),
            "name": name
        }))

    def handle_enable_intent(self, message):
        """
        Listener to enable a registered intent if it belongs to this skill
        """
        intent_name = message.data["intent_name"]
        for (name, intent) in self.registered_intents:
            if name == intent_name:
                return self.enable_intent(intent_name)

    def handle_disable_intent(self, message):
        """
        Listener to disable a registered intent if it belongs to this skill
        """
        intent_name = message.data["intent_name"]
        for (name, intent) in self.registered_intents:
            if name == intent_name:
                return self.disable_intent(intent_name)

    def disable_intent(self, intent_name):
        """
        Disable a registered intent if it belongs to this skill

        Args:
                intent_name: name of the intent to be disabled

        Returns:
                bool: True if disabled, False if it wasn't registered
        """
        names = [intent_tuple[0] for intent_tuple in self.registered_intents]
        if intent_name in names:
            LOG.debug('Disabling intent ' + intent_name)
            name = str(self.skill_id) + ':' + intent_name
            self.emitter.emit(
                Message("detach_intent", {"intent_name": name}))
            return True
        LOG.error('Could not disable ' + intent_name +
                  ', it hasn\'t been registered.')
        return False

    def enable_intent(self, intent_name):
        """
        (Re)Enable a registered intentif it belongs to this skill

        Args:
                intent_name: name of the intent to be enabled

        Returns:
                bool: True if enabled, False if it wasn't registered
        """
        names = [intent[0] for intent in self.registered_intents]
        intents = [intent[1] for intent in self.registered_intents]
        if intent_name in names:
            intent = intents[names.index(intent_name)]
            self.registered_intents.remove((intent_name, intent))
            intent.name = intent_name
            self.register_intent(intent, None)
            LOG.debug('Enabling intent ' + intent_name)
            return True
        LOG.error('Could not enable ' + intent_name + ', it hasn\'t been '
                                                      'registered.')
        return False

    def set_context(self, context, word=''):
        """
            Add context to intent service

            Args:
                context:    Keyword
                word:       word connected to keyword
        """
        if not isinstance(context, basestring):
            raise ValueError('context should be a string')
        if not isinstance(word, basestring):
            raise ValueError('word should be a string')
        context = to_letters(self.skill_id) + context
        self.emitter.emit(Message('add_context',
                                  {'context': context, 'word': word}))

    def remove_context(self, context):
        """
            remove_context removes a keyword from from the context manager.
        """
        if not isinstance(context, basestring):
            raise ValueError('context should be a string')
        self.emitter.emit(Message('remove_context', {'context': context}))

    def register_vocabulary(self, entity, entity_type):
        """ Register a word to an keyword

            Args:
                entity:         word to register
                entity_type:    Intent handler entity to tie the word to
        """
        self.emitter.emit(Message('register_vocab', {
            'start': entity, 'end': to_letters(self.skill_id) + entity_type
        }))

    def register_regex(self, regex_str):
        """ Register a new regex.
            Args:
                regex_str: Regex string
        """
        regex = munge_regex(regex_str, self.skill_id)
        re.compile(regex)  # validate regex
        self.emitter.emit(Message('register_vocab', {'regex': regex}))

    def speak(self, utterance, expect_response=False):
        """
            Speak a sentence.

            Args:
                utterance (str):        sentence mycroft should speak
                expect_response (bool): set to True if Mycroft should listen
                                        for a response immediately after
                                        speaking the utterance.
        """
        # registers the skill as being active
        self.enclosure.register(self.name)
        data = {'utterance': utterance,
                'expect_response': expect_response}
        message = dig_for_message()
        if message:
            self.emitter.emit(message.reply("speak", data))
        else:
            self.emitter.emit(Message("speak", data))

    def speak_dialog(self, key, data=None, expect_response=False):
        """
            Speak a random sentence from a dialog file.

            Args
                key (str): dialog file key (filename without extension)
                data (dict): information used to populate sentence
                expect_response (bool): set to True if Mycroft should listen
                                        for a response immediately after
                                        speaking the utterance.
        """
        data = data or {}
        self.speak(self.dialog_renderer.render(key, data), expect_response)

    def init_dialog(self, root_directory):
        dialog_dir = join(root_directory, 'dialog', self.lang)
        if exists(dialog_dir):
            self.dialog_renderer = DialogLoader().load(dialog_dir)
        else:
            LOG.debug('No dialog loaded, ' + dialog_dir + ' does not exist')

    def load_data_files(self, root_directory):
        self.init_dialog(root_directory)
        self.load_vocab_files(join(root_directory, 'vocab', self.lang))
        regex_path = join(root_directory, 'regex', self.lang)
        self.root_dir = root_directory
        if exists(regex_path):
            self.load_regex_files(regex_path)

    def load_vocab_files(self, vocab_dir):
        self.vocab_dir = vocab_dir
        if exists(vocab_dir):
            load_vocabulary(vocab_dir, self.emitter, self.skill_id)
        else:
            LOG.debug('No vocab loaded, ' + vocab_dir + ' does not exist')

    def load_regex_files(self, regex_dir):
        load_regex(regex_dir, self.emitter, self.skill_id)

    def __handle_stop(self, event):
        """
            Handler for the "mycroft.stop" signal. Runs the user defined
            `stop()` method.
        """
        self.stop_time = time.time()
        try:
            self.stop()
        except:
            LOG.error("Failed to stop skill: {}".format(self.name),
                      exc_info=True)

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
        pass

    def _shutdown(self):
        """Parent function called internally to shut down everything"""
        try:
            self.shutdown()
        except exception as e:
            LOG.error('Skill specific shutdown function encountered '
                      'an error: {}'.format(repr(e)))
        # Store settings
        self.settings.store()
        self.settings.stop_polling()
        # removing events
        self.cancel_all_repeating_events()
        for e, f in self.events:
            self.emitter.remove(e, f)
        self.events = []  # Remove reference to wrappers

        self.emitter.emit(
            Message("detach_skill", {"skill_id": str(self.skill_id) + ":"}))
        try:
            self.stop()
        except:
            LOG.error("Failed to stop skill: {}".format(self.name),
                      exc_info=True)

    def _unique_name(self, name):
        """
            Return a name unique to this skill using the format
            [skill_id]:[name].

            Args:
                name:   Name to use internally

            Returns:
                str: name unique to this skill
        """
        return str(self.skill_id) + ':' + (name or '')

    def _schedule_event(self, handler, when, data=None, name=None,
                        repeat=None):
        """
            Underlying method for schedule_event and schedule_repeating_event.
            Takes scheduling information and sends it of on the message bus.
        """
        if not name:
            name = self.name + handler.__name__
        name = self._unique_name(name)
        if repeat:
            self.scheduled_repeats.append(name)

        data = data or {}
        self.add_event(name, handler, once=not repeat)
        event_data = {}
        event_data['time'] = time.mktime(when.timetuple())
        event_data['event'] = name
        event_data['repeat'] = repeat
        event_data['data'] = data
        self.emitter.emit(Message('mycroft.scheduler.schedule_event',
                                  data=event_data))

    def schedule_event(self, handler, when, data=None, name=None):
        """
            Schedule a single event.

            Args:
                handler:               method to be called
                when (datetime):       when the handler should be called
                data (dict, optional): data to send when the handler is called
                name (str, optional):  friendly name parameter
        """
        data = data or {}
        self._schedule_event(handler, when, data, name)

    def schedule_repeating_event(self, handler, when, frequency,
                                 data=None, name=None):
        """
            Schedule a repeating event.

            Args:
                handler:                method to be called
                when (datetime):        time for calling the handler or None
                                        to initially trigger <frequency>
                                        seconds from now
                frequency (float/int):  time in seconds between calls
                data (dict, optional):  data to send along to the handler
                name (str, optional):   friendly name parameter
        """
        # Do not schedule if this event is already scheduled by the skill
        if name not in self.scheduled_repeats:
            data = data or {}
            if not when:
                when = datetime.now() + timedelta(seconds=frequency)
            self._schedule_event(handler, when, data, name, frequency)
        else:
            LOG.debug('The event is already scheduled, cancel previous '
                      'event if this scheduling should replace the last.')

    def update_scheduled_event(self, name, data=None):
        """
            Change data of event.

            Args:
                name (str):   Name of event
        """
        data = data or {}
        data = {
            'event': self._unique_name(name),
            'data': data
        }
        self.emitter.emit(Message('mycroft.schedule.update_event', data=data))

    def cancel_scheduled_event(self, name):
        """
            Cancel a pending event. The event will no longer be scheduled
            to be executed

            Args:
                name (str):   Name of event
        """
        unique_name = self._unique_name(name)
        data = {'event': unique_name}
        if name in self.scheduled_repeats:
            self.scheduled_repeats.remove(name)
        if self.remove_event(unique_name):
            self.emitter.emit(Message('mycroft.scheduler.remove_event',
                                      data=data))

    def get_scheduled_event_status(self, name):
        """
            Get scheduled event data and return the amount of time left

            Args:
                name (str): Name of event

            Return:
                int: the time left in seconds
        """
        event_name = self._unique_name(name)
        data = {'name': event_name}

        # making event_status an object so it's refrence can be changed
        event_status = [None]
        finished_callback = [False]

        def callback(message):
            if message.data is not None:
                event_time = int(message.data[0][0])
                current_time = int(time.time())
                time_left_in_seconds = event_time - current_time
                event_status[0] = time_left_in_seconds
            finished_callback[0] = True

        emitter_name = 'mycroft.event_status.callback.{}'.format(event_name)
        self.emitter.once(emitter_name, callback)
        self.emitter.emit(Message('mycroft.scheduler.get_event', data=data))

        start_wait = time.time()
        while finished_callback[0] is False and time.time() - start_wait < 3.0:
            time.sleep(0.1)
        if time.time() - start_wait > 3.0:
            raise Exception("Event Status Messagebus Timeout")
        return event_status[0]

    def cancel_all_repeating_events(self):
        """ Cancel any repeating events started by the skill. """
        for e in self.scheduled_repeats:
            self.cancel_scheduled_event(e)


#######################################################################
# FallbackSkill base class
#######################################################################
class FallbackSkill(MycroftSkill):
    """
        FallbackSkill is used to declare a fallback to be called when
        no skill is matching an intent. The fallbackSkill implements a
        number of fallback handlers to be called in an order determined
        by their priority.
    """
    fallback_handlers = {}

    def __init__(self, name=None, emitter=None):
        MycroftSkill.__init__(self, name, emitter)

        #  list of fallback handlers registered by this instance
        self.instance_fallback_handlers = []

    @classmethod
    def make_intent_failure_handler(cls, ws):
        """Goes through all fallback handlers until one returns True"""

        def handler(message):
            # indicate fallback handling start
            ws.emit(Message("mycroft.skill.handler.start",
                            data={'handler': "fallback"}))

            stopwatch = Stopwatch()
            handler_name = None
            with stopwatch:
                for _, handler in sorted(cls.fallback_handlers.items(),
                                         key=operator.itemgetter(0)):
                    try:
                        if handler(message):
                            #  indicate completion
                            handler_name = get_handler_name(handler)
                            ws.emit(Message(
                                'mycroft.skill.handler.complete',
                                data={'handler': "fallback",
                                      "fallback_handler": handler_name}))
                            break
                    except Exception:
                        LOG.exception('Exception in fallback.')
                else:  # No fallback could handle the utterance
                    ws.emit(Message('complete_intent_failure'))
                    warning = "No fallback could handle intent."
                    LOG.warning(warning)
                    #  indicate completion with exception
                    ws.emit(Message('mycroft.skill.handler.complete',
                                    data={'handler': "fallback",
                                          'exception': warning}))

            # Send timing metric
            if message.context and message.context['ident']:
                ident = message.context['ident']
                report_timing(ident, 'fallback_handler', stopwatch,
                              {'handler': handler_name})

        return handler

    @classmethod
    def _register_fallback(cls, handler, priority):
        """
        Register a function to be called as a general info fallback
        Fallback should receive message and return
        a boolean (True if succeeded or False if failed)

        Lower priority gets run first
        0 for high priority 100 for low priority
        """
        while priority in cls.fallback_handlers:
            priority += 1

        cls.fallback_handlers[priority] = handler

    def register_fallback(self, handler, priority):
        """
            register a fallback with the list of fallback handlers
            and with the list of handlers registered by this instance
        """

        def wrapper(*args, **kwargs):
            if handler(*args, **kwargs):
                self.make_active()
                return True
            return False

        self.instance_fallback_handlers.append(wrapper)
        self._register_fallback(handler, priority)

    @classmethod
    def remove_fallback(cls, handler_to_del):
        """
            Remove a fallback handler

            Args:
                handler_to_del: reference to handler
        """
        for priority, handler in cls.fallback_handlers.items():
            if handler == handler_to_del:
                del cls.fallback_handlers[priority]
                return
        LOG.warning('Could not remove fallback!')

    def remove_instance_handlers(self):
        """
            Remove all fallback handlers registered by the fallback skill.
        """
        while len(self.instance_fallback_handlers):
            handler = self.instance_fallback_handlers.pop()
            self.remove_fallback(handler)

    def _shutdown(self):
        """
            Remove all registered handlers and perform skill shutdown.
        """
        self.remove_instance_handlers()
        super(FallbackSkill, self)._shutdown()
