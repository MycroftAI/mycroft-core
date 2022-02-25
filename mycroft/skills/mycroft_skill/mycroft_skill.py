# Copyright 2019 Mycroft AI Inc.
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
"""Common functionality relating to the implementation of mycroft skills."""

import re
import sys
import traceback
from copy import copy
from inspect import signature
from itertools import chain
from os import walk, listdir
from os.path import join, abspath, dirname, basename, exists, isdir
import shutil
from threading import Event

from adapt.intent import Intent, IntentBuilder
from json_database import JsonStorage

from mycroft import dialog
from mycroft.api import DeviceApi
from mycroft.audio import wait_while_speaking
from mycroft.configuration import Configuration
from mycroft.dialog import load_dialogs
from mycroft.filesystem import FileSystemAccess
from mycroft.gui import SkillGUI
from mycroft.messagebus.message import Message, dig_for_message
from mycroft.metrics import report_metric
from mycroft.skills.event_scheduler import EventSchedulerInterface
from mycroft.skills.intent_service_interface import IntentServiceInterface
from mycroft.skills.mycroft_skill.event_container import EventContainer, \
    create_wrapper, get_handler_name
from mycroft.skills.skill_data import (
    load_vocabulary,
    load_regex,
    to_alnum,
    munge_regex,
    munge_intent_parser,
    read_vocab_file,
    read_value_file,
    read_translated_file
)
from mycroft.util import (
    resolve_resource_file,
    play_audio_file,
    camel_case_split
)
from mycroft.util.format import pronounce_number, join_list
from mycroft.util.log import LOG
from mycroft.util.parse import match_one, extract_number
from ovos_utils.configuration import is_using_xdg, get_xdg_base, get_xdg_data_save_path
from ovos_utils.enclosure.api import EnclosureAPI
from ovos_utils.file_utils import get_temp_path
import shutil


def simple_trace(stack_trace):
    """Generate a simplified traceback.

    Args:
        stack_trace: Stack trace to simplify

    Returns: (str) Simplified stack trace.
    """
    stack_trace = stack_trace[:-1]
    tb = 'Traceback:\n'
    for line in stack_trace:
        if line.strip():
            tb += line
    return tb


def get_non_properties(obj):
    """Get attibutes that are not properties from object.

    Will return members of object class along with bases down to MycroftSkill.

    Args:
        obj: object to scan

    Returns:
        Set of attributes that are not a property.
    """

    def check_class(cls):
        """Find all non-properties in a class."""
        # Current class
        d = cls.__dict__
        np = [k for k in d if not isinstance(d[k], property)]
        # Recurse through base classes excluding MycroftSkill and object
        for b in [b for b in cls.__bases__ if b not in (object, MycroftSkill)]:
            np += check_class(b)
        return np

    return set(check_class(obj.__class__))


class MycroftSkill:
    """Base class for mycroft skills providing common behaviour and parameters
    to all Skill implementations.

    For information on how to get started with creating mycroft skills see
    https://mycroft.ai/documentation/skills/introduction-developing-skills/

    Args:
        name (str): skill name
        bus (MycroftWebsocketClient): Optional bus connection
        use_settings (bool): Set to false to not use skill settings at all (DEPRECATED)
    """

    def __init__(self, name=None, bus=None, use_settings=True):
        self._init_event = Event()

        self.name = name or self.__class__.__name__
        self.resting_name = None
        self.skill_id = ''  # will be set by SkillLoader, guaranteed unique
        self.settings_meta = None  # set when skill is loaded in SkillLoader

        # Get directory of skill
        #: Member variable containing the absolute path of the skill's root
        #: directory. E.g. $XDG_DATA_HOME/mycroft/skills/my-skill.me/
        self.root_dir = dirname(abspath(sys.modules[self.__module__].__file__))

        self.gui = SkillGUI(self)

        self._bus = None
        self._enclosure = EnclosureAPI()

        #: Mycroft global configuration. (dict)
        self.config_core = Configuration.get()

        self._settings = None
        self._initial_settings = {}
        self.settings_write_path = None

        # old kludge from fallback skills, unused according to grep
        if use_settings is False:
            LOG.warning("use_settings has been deprecated! skill settings are always enabled")

        #: Set to register a callback method that will be called every time
        #: the skills settings are updated. The referenced method should
        #: include any logic needed to handle the updated settings.
        self.settings_change_callback = None

        self.dialog_renderers = {}

        # fully initialized when self.skill_id is set
        self._file_system = None

        self.log = LOG
        self.reload_skill = True  #: allow reloading (default True)

        self.events = EventContainer(bus)
        self.voc_match_cache = {}

        # Delegator classes
        self.event_scheduler = EventSchedulerInterface()
        self.intent_service = IntentServiceInterface()

        # Skill Public API
        self.public_api = {}

    @property
    def is_fully_initialized(self):
        """Determines if the skill has been fully loaded and setup.
        When True all data has been loaded and all internal state and events setup"""
        return self._init_event.is_set()

    def handle_first_run(self):
        """The very first time a skill is run, speak the intro."""
        intro = self.get_intro_message()
        if intro:
            # supports .dialog files for easy localization
            # when .dialog does not exist, the text is spoken
            # it is backwards compatible
            self.speak_dialog(intro)

    def _check_for_first_run(self):
        """Determine if its the very first time a skill is run."""
        first_run = self.settings.get("__mycroft_skill_firstrun", True)
        if first_run:
            LOG.info("First run of " + self.skill_id)
            self.handle_first_run()
            self.settings["__mycroft_skill_firstrun"] = False
            self.settings.store()

    def _startup(self, bus, skill_id=""):
        """Startup the skill.

        This connects the skill to the messagebus, loads vocabularies and
        data files and in the end calls the skill creator's "intialize" code.

        Arguments:
            bus: Mycroft Messagebus connection object.
            skill_id (str): need to be unique, by default is set from skill path
                but skill loader can override this
        """
        if self.is_fully_initialized:
            LOG.warning(f"Tried to initialize {self.skill_id} multiple times, ignoring")
            return

        # NOTE: this method is called by SkillLoader
        # it is private to make it clear to skill devs they should not touch it
        try:
            # set the skill_id
            self.skill_id = skill_id or basename(self.root_dir)
            self.intent_service.set_id(self.skill_id)
            self.event_scheduler.set_id(self.skill_id)
            self.enclosure.set_id(self.skill_id)

            # initialize anything that depends on skill_id
            self.log = LOG.create_logger(self.skill_id)
            self._init_settings()

            # initialize anything that depends on the messagebus
            self.bind(bus)
            self.load_data_files()
            self._register_decorated()
            self.register_resting_screen()

            # run skill developer initialization code
            self.initialize()
            self._check_for_first_run()
            self._init_event.set()
        except Exception as e:
            LOG.exception('Skill initialization failed')
            # If an exception occurs, attempt to clean up the skill
            try:
                self.default_shutdown()
            except Exception as e2:
                pass
            raise e

    def _init_settings(self):
        """Setup skill settings."""
        LOG.debug(f"initializing skill settings for {self.skill_id}")

        # migrate settings if needed
        if not exists(self._settings_path) and exists(self._old_settings_path):
            shutil.copy(self._old_settings_path, self._settings_path)

        # NOTE: lock is disabled due to usage of deepcopy and to allow json serialization
        self._settings = JsonStorage(self._settings_path, disable_lock=True)
        if self._initial_settings:
            # TODO make a debug log in next version
            LOG.warning("Copying default settings values defined in __init__ \n"
                        "Please move code from __init__() to initialize() if you did not expect to see this message")
            for k, v in self._initial_settings.items():
                if k not in self._settings:
                    self._settings[k] = v
        self._initial_settings = copy(self.settings)

    @property
    def _old_settings_path(self):
        old_dir = self.config_core.get("data_dir", "/opt/mycroft")
        old_folder = self.config_core.get("skills", {}).get("msm", {}).get("directory", "skills")
        return join(old_dir, old_folder, self.skill_id, 'settings.json')

    @property
    def _settings_path(self):
        is_xdg = is_using_xdg()
        if self.settings_write_path:
            LOG.warning("self.settings_write_path has been deprecated! "
                        "Support will be dropped in a future release")
            return join(self.settings_write_path, 'settings.json')
        if not is_xdg:
            return self._old_settings_path
        return join(get_xdg_data_save_path(), 'skills', self.skill_id, 'settings.json')

    @property
    def settings(self):
        if self._settings is not None:
            return self._settings
        else:
            LOG.error('Skill not fully initialized. '
                      'Only default values can be set, no settings can be read or changed.'
                      'Move code from  __init__() to initialize() to correct this.')
            return self._initial_settings

    @settings.setter
    def settings(self, val):
        assert isinstance(val, dict)
        # init method
        if self._settings is None:
            self._initial_settings = val
            return
        # ensure self._settings remains a JsonDatabase
        self._settings.clear()  # clear data
        self._settings.merge(val)  # merge new data

    @property
    def dialog_renderer(self):
        if self.lang in self.dialog_renderers:
            return self.dialog_renderers[self.lang]
        # Try to load the renderer
        self._load_dialog_files(self.root_dir, self.lang)
        if self.lang in self.dialog_renderers:
            return self.dialog_renderers[self.lang]
        # Fall back to main language
        return self.dialog_renderers.get(self._core_lang)

    @property
    def enclosure(self):
        if self._enclosure:
            return self._enclosure
        else:
            LOG.error('Skill not fully initialized. Move code ' +
                      'from  __init__() to initialize() to correct this.')
            LOG.error(simple_trace(traceback.format_stack()))
            raise Exception('Accessed MycroftSkill.enclosure in __init__')

    @property
    def file_system(self):
        """ Filesystem access to skill specific folder.

        See mycroft.filesystem for details.
        """
        if not self._file_system and self.skill_id:
            self._file_system = FileSystemAccess(join('skills', self.skill_id))
        if self._file_system:
            return self._file_system
        else:
            LOG.error('Skill not fully initialized. Move code ' +
                      'from  __init__() to initialize() to correct this.')
            LOG.error(simple_trace(traceback.format_stack()))
            raise Exception('Accessed MycroftSkill.file_system in __init__')

    @file_system.setter
    def file_system(self, fs):
        """Provided mainly for backwards compatibility with derivative MycroftSkill classes
        Skills are advised against redefining the file system directory"""
        self._file_system = fs

    @property
    def bus(self):
        if self._bus:
            return self._bus
        else:
            LOG.error('Skill not fully initialized. Move code ' +
                      'from __init__() to initialize() to correct this.')
            LOG.error(simple_trace(traceback.format_stack()))
            raise Exception('Accessed MycroftSkill.bus in __init__')

    @property
    def location(self):
        """Get the JSON data struction holding location information."""
        # TODO: Allow Enclosure to override this for devices that
        # contain a GPS.
        return self.config_core.get('location')

    @property
    def location_pretty(self):
        """Get a more 'human' version of the location as a string."""
        loc = self.location
        if type(loc) is dict and loc['city']:
            return loc['city']['name']
        return None

    @property
    def location_timezone(self):
        """Get the timezone code, such as 'America/Los_Angeles'"""
        loc = self.location
        if type(loc) is dict and loc['timezone']:
            return loc['timezone']['code']
        return None

    @property
    def lang(self):
        """Get the current language."""
        lang = self._core_lang
        message = dig_for_message()
        if message:
            lang = message.data.get("lang") or lang
        return lang.lower()

    @property
    def _core_lang(self):
        """Get the configured default language.
        NOTE: this should be public, but since if a skill uses this it wont
        work in regular mycroft-core it was made private! Equivalent PRs in
        mycroft-core have been rejected/abandoned"""
        return Configuration.get().get("lang", "en-us").lower()

    @property
    def _secondary_langs(self):
        """Get the configured secondary languages, mycroft is not
        considered to be in these languages but i will load it's resource
        files. This provides initial support for multilingual input
        NOTE: this should be public, but since if a skill uses this it wont
        work in regular mycroft-core it was made private! Equivalent PRs in
        mycroft-core have been rejected/abandoned
        """
        return [l.lower() for l in self.config_core.get('secondary_langs', [])
                if l != self._core_lang]

    def _get_language_dir(self, base_path, lang=None):
        """ checks for all language variations and returns best path
        eg, if lang is set to pt-pt but only pt-br resources exist,
        those will be loaded instead of failing, or en-gb vs en-us and so on
        NOTE: this should be public, but since if a skill uses this it wont
        work in regular mycroft-core it was made private! Equivalent PRs in
        mycroft-core have been rejected/abandoned
        """
        # NOTE this should not be private, but for backwards compat with
        # mycroft-core it is, dont want skills to call it directly
        lang = lang or self.lang
        lang_path = join(base_path, lang)

        # base_path/en-us
        if isdir(lang_path):
            return lang_path
        if "-" in lang:
            lang2 = lang.split("-")[0]
            # base_path/en
            general_lang_path = join(base_path, lang2)
            if isdir(general_lang_path):
                return general_lang_path
        else:
            lang2 = lang

        # base_path/en-uk, base_path/en-au...
        if isdir(base_path):
            # TODO how to choose best local dialect?
            for path in [join(base_path, f)
                         for f in listdir(base_path) if f.startswith(lang2)]:
                if isdir(path):
                    return path
        return join(base_path, lang)

    def bind(self, bus):
        """Register messagebus emitter with skill.

        Args:
            bus: Mycroft messagebus connection
        """
        if bus:
            self._bus = bus
            self.events.set_bus(bus)
            self.intent_service.set_bus(bus)
            self.event_scheduler.set_bus(bus)
            self._enclosure.set_bus(bus)
            self._register_system_event_handlers()
            # Initialize the SkillGui
            self.gui.setup_default_handlers()

            self._register_public_api()

    def _register_public_api(self):
        """ Find and register api methods.
        Api methods has been tagged with the api_method member, for each
        method where this is found the method a message bus handler is
        registered.
        Finally create a handler for fetching the api info from any requesting
        skill.
        """

        def wrap_method(func):
            """Boiler plate for returning the response to the sender."""

            def wrapper(message):
                result = func(*message.data['args'], **message.data['kwargs'])
                message.context["skill_id"] = self.skill_id
                self.bus.emit(message.response(data={'result': result}))

            return wrapper

        methods = [attr_name for attr_name in get_non_properties(self)
                   if hasattr(getattr(self, attr_name), '__name__')]

        for attr_name in methods:
            method = getattr(self, attr_name)

            if hasattr(method, 'api_method'):
                doc = method.__doc__ or ''
                name = method.__name__
                self.public_api[name] = {
                    'help': doc,
                    'type': f'{self.skill_id}.{name}',
                    'func': method
                }
        for key in self.public_api:
            if ('type' in self.public_api[key] and
                    'func' in self.public_api[key]):
                LOG.debug(f"Adding api method: {self.public_api[key]['type']}")

                # remove the function member since it shouldn't be
                # reused and can't be sent over the messagebus
                func = self.public_api[key].pop('func')
                self.add_event(self.public_api[key]['type'],
                               wrap_method(func))

        if self.public_api:
            self.add_event(f'{self.skill_id}.public_api',
                           self._send_public_api)

    @property
    def stop_is_implemented(self):
        return self.__class__.stop is not MycroftSkill.stop

    @property
    def converse_is_implemented(self):
        return self.__class__.converse is not MycroftSkill.converse

    def _register_system_event_handlers(self):
        """Add all events allowing the standard interaction with the Mycroft
        system.
        """
        # Only register stop if it's been implemented
        if self.stop_is_implemented:
            self.add_event('mycroft.stop', self.__handle_stop)
        self.add_event('skill.converse.ping', self._handle_converse_ack)
        self.add_event('skill.converse.request', self._handle_converse_request)
        self.add_event(f"{self.skill_id}.activate", self.handle_activate)
        self.add_event(f"{self.skill_id}.deactivate", self.handle_deactivate)
        self.add_event("intent.service.skills.deactivated", self._handle_skill_deactivated)
        self.add_event("intent.service.skills.activated", self._handle_skill_activated)
        self.add_event('mycroft.skill.enable_intent', self.handle_enable_intent)
        self.add_event('mycroft.skill.disable_intent', self.handle_disable_intent)
        self.add_event('mycroft.skill.set_cross_context', self.handle_set_cross_context)
        self.add_event('mycroft.skill.remove_cross_context', self.handle_remove_cross_context)
        self.add_event('mycroft.skills.settings.changed', self.handle_settings_change)

    def handle_settings_change(self, message):
        """Update settings if the remote settings changes apply to this skill.

        The skill settings downloader uses a single API call to retrieve the
        settings for all skills.  This is done to limit the number API calls.
        A "mycroft.skills.settings.changed" event is emitted for each skill
        that had their settings changed.  Only update this skill's settings
        if its remote settings were among those changed
        """
        if self.settings_meta is None or self.settings_meta.skill_gid is None:
            LOG.error('The skill_gid was not set when '
                      '{} was loaded!'.format(self.name))
        else:
            remote_settings = message.data.get(self.settings_meta.skill_gid)
            if remote_settings is not None:
                LOG.info('Updating settings for skill ' + self.skill_id)
                self.settings.update(**remote_settings)
                self.settings.store()
                if self.settings_change_callback is not None:
                    self.settings_change_callback()

    def detach(self):
        for (name, _) in self.intent_service:
            name = f'{self.skill_id}:{name}'
            self.intent_service.detach_intent(name)

    def initialize(self):
        """Perform any final setup needed for the skill.

        Invoked after the skill is fully constructed and registered with the
        system.
        """
        pass

    def _send_public_api(self, message):
        """Respond with the skill's public api."""
        message.context["skill_id"] = self.skill_id
        self.bus.emit(message.response(data=self.public_api))

    def get_intro_message(self):
        """Get a message to speak on first load of the skill.

        Useful for post-install setup instructions.

        Returns:
            str: message that will be spoken to the user
        """
        return None

    # converse handling
    def _handle_skill_activated(self, message):
        """ intent service activated a skill
        if it was this skill fire the skill activation event"""
        if message.data.get("skill_id") == self.skill_id:
            self.bus.emit(message.forward(f"{self.skill_id}.activate"))

    def handle_activate(self, message):
        """ skill is now considered active by the intent service
        converse method will be called, skills might want to prepare/resume
        """

    def _handle_skill_deactivated(self, message):
        """ intent service deactivated a skill
        if it was this skill fire the skill deactivation event"""
        if message.data.get("skill_id") == self.skill_id:
            self.bus.emit(message.forward(f"{self.skill_id}.deactivate"))

    def handle_deactivate(self, message):
        """ skill is no longer considered active by the intent service
        converse method will not be called, skills might want to reset state here
        """

    def activate(self):
        """Bump skill to active_skill list in intent_service.
        This enables converse method to be called even without skill being
        used in last 5 minutes.
        """
        msg = dig_for_message() or Message("")
        if "skill_id" not in msg.context:
            msg.context["skill_id"] = self.skill_id
        self.bus.emit(msg.forward("intent.service.skills.activate",
                                  data={"skill_id": self.skill_id}))

    def deactivate(self):
        """remove skill from active_skill list in intent_service.
        This stops converse method from being called
        """
        msg = dig_for_message() or Message("")
        if "skill_id" not in msg.context:
            msg.context["skill_id"] = self.skill_id
        self.bus.emit(msg.forward(f"intent.service.skills.deactivate",
                                  data={"skill_id": self.skill_id}))

    def _handle_converse_ack(self, message):
        """Inform skills service if we want to handle converse.
        individual skills may override the property self.converse_is_implemented"""
        self.bus.emit(message.reply(
            "skill.converse.pong",
            data={"skill_id": self.skill_id,
                  "can_handle": self.converse_is_implemented},
            context={"skill_id": self.skill_id}))

    def _handle_converse_request(self, message):
        """Check if the targeted skill id can handle conversation
        If supported, the conversation is invoked.
        """
        skill_id = message.data['skill_id']
        if skill_id == self.skill_id:
            try:
                # converse can have multiple signatures
                params = signature(self.converse).parameters
                kwargs = {"message": message,
                          "utterances": message.data['utterances'],
                          "lang": message.data['lang']}
                kwargs = {k: v for k, v in kwargs.items() if k in params}
                result = self.converse(**kwargs)
                self.bus.emit(message.reply('skill.converse.response',
                                            {"skill_id": self.skill_id,
                                             "result": result}))
            except Exception:
                self.bus.emit(message.reply('skill.converse.response',
                                            {"skill_id": self.skill_id,
                                             "result": False}))

    def converse(self, message=None):
        """Handle conversation.

        This method gets a peek at utterances before the normal intent
        handling process after a skill has been invoked once.

        To use, override the converse() method and return True to
        indicate that the utterance has been handled.

        utterances and lang are depreciated

        Args:
            message:    a message object containing a message type with an
                        optional JSON data packet

        Returns:
            bool: True if an utterance was handled, otherwise False
        """
        return False

    def __get_response(self):
        """Helper to get a response from the user

        NOTE:  There is a race condition here.  There is a small amount of
        time between the end of the device speaking and the converse method
        being overridden in this method.  If an utterance is injected during
        this time, the wrong converse method is executed.  The condition is
        hidden during normal use due to the amount of time it takes a user
        to speak a response. The condition is revealed when an automated
        process injects an utterance quicker than this method can flip the
        converse methods.

        Returns:
            str: user's response or None on a timeout
        """
        event = Event()

        def converse(utterances, lang=None):
            converse.response = utterances[0] if utterances else None
            event.set()
            return True

        # install a temporary conversation handler
        self.activate()
        converse.response = None
        default_converse = self.converse
        self.converse = converse
        event.wait(15)  # 10 for listener, 5 for SST, then timeout
        self.converse = default_converse
        return converse.response

    def get_response(self, dialog='', data=None, validator=None,
                     on_fail=None, num_retries=-1):
        """Get response from user.

        If a dialog is supplied it is spoken, followed immediately by listening
        for a user response. If the dialog is omitted listening is started
        directly.

        The response can optionally be validated before returning.

        Example::

            color = self.get_response('ask.favorite.color')

        Args:
            dialog (str): Optional dialog to speak to the user
            data (dict): Data used to render the dialog
            validator (any): Function with following signature::

                def validator(utterance):
                    return utterance != "red"

            on_fail (any):
                Dialog or function returning literal string to speak on
                invalid input. For example::

                    def on_fail(utterance):
                        return "nobody likes the color red, pick another"

            num_retries (int): Times to ask user for input, -1 for infinite
                NOTE: User can not respond and timeout or say "cancel" to stop

        Returns:
            str: User's reply or None if timed out or canceled
        """
        data = data or {}

        def on_fail_default(utterance):
            fail_data = data.copy()
            fail_data['utterance'] = utterance
            if on_fail:
                if self.dialog_renderer:
                    return self.dialog_renderer.render(on_fail, fail_data)
                return on_fail
            else:
                if self.dialog_renderer:
                    return self.dialog_renderer.render(dialog, data)
                return dialog

        def is_cancel(utterance):
            return self.voc_match(utterance, 'cancel')

        def validator_default(utterance):
            # accept anything except 'cancel'
            return not is_cancel(utterance)

        on_fail_fn = on_fail if callable(on_fail) else on_fail_default
        validator = validator or validator_default

        # Speak query and wait for user response
        if dialog:
            self.speak_dialog(dialog, data, expect_response=True, wait=True)
        else:
            msg = dig_for_message()
            msg = msg.reply('mycroft.mic.listen') if msg else \
                Message('mycroft.mic.listen', context={"skill_id": self.skill_id})
            self.bus.emit(msg)
        return self._wait_response(is_cancel, validator, on_fail_fn,
                                   num_retries)

    def _wait_response(self, is_cancel, validator, on_fail, num_retries):
        """Loop until a valid response is received from the user or the retry
        limit is reached.

        Args:
            is_cancel (callable): function checking cancel criteria
            validator (callbale): function checking for a valid response
            on_fail (callable): function handling retries

        """
        msg = dig_for_message()
        msg = msg.reply('mycroft.mic.listen') if msg else \
            Message('mycroft.mic.listen',
                    context={"skill_id": self.skill_id})

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

            line = on_fail(response)
            if line:
                self.speak(line, expect_response=True)
            else:
                self.bus.emit(msg)

    def ask_yesno(self, prompt, data=None):
        """Read prompt and wait for a yes/no answer

        This automatically deals with translation and common variants,
        such as 'yeah', 'sure', etc.

        Args:
              prompt (str): a dialog id or string to read
              data (dict): response data
        Returns:
              string:  'yes', 'no' or whatever the user response if not
                       one of those, including None
        """
        resp = self.get_response(dialog=prompt, data=data)

        if self.voc_match(resp, 'yes'):
            return 'yes'
        elif self.voc_match(resp, 'no'):
            return 'no'
        else:
            return resp

    def ask_selection(self, options, dialog='',
                      data=None, min_conf=0.65, numeric=False):
        """Read options, ask dialog question and wait for an answer.

        This automatically deals with fuzzy matching and selection by number
        e.g.

        * "first option"
        * "last option"
        * "second option"
        * "option number four"

        Args:
              options (list): list of options to present user
              dialog (str): a dialog id or string to read AFTER all options
              data (dict): Data used to render the dialog
              min_conf (float): minimum confidence for fuzzy match, if not
                                reached return None
              numeric (bool): speak options as a numeric menu
        Returns:
              string: list element selected by user, or None
        """
        assert isinstance(options, list)

        if not len(options):
            return None
        elif len(options) == 1:
            return options[0]

        if numeric:
            for idx, opt in enumerate(options):
                number = pronounce_number(idx + 1, self.lang)
                self.speak(f"{number}, {opt}", wait=True)
        else:
            opt_str = join_list(options, "or", lang=self.lang) + "?"
            self.speak(opt_str, wait=True)

        resp = self.get_response(dialog=dialog, data=data)

        if resp:
            match, score = match_one(resp, options)
            if score < min_conf:
                if self.voc_match(resp, 'last'):
                    resp = options[-1]
                else:
                    num = extract_number(resp, ordinals=True, lang=self.lang)
                    resp = None
                    if num and num <= len(options):
                        resp = options[num - 1]
            else:
                resp = match
        return resp

    def voc_match(self, utt, voc_filename, lang=None, exact=False):
        """Determine if the given utterance contains the vocabulary provided.

        By default the method checks if the utterance contains the given vocab
        thereby allowing the user to say things like "yes, please" and still
        match against "Yes.voc" containing only "yes". An exact match can be
        requested.

        The method first checks in the current Skill's .voc files and secondly
        in the "res/text" folder of mycroft-core. The result is cached to
        avoid hitting the disk each time the method is called.

        Args:
            utt (str): Utterance to be tested
            voc_filename (str): Name of vocabulary file (e.g. 'yes' for
                                'res/text/en-us/yes.voc')
            lang (str): Language code, defaults to self.lang
            exact (bool): Whether the vocab must exactly match the utterance

        Returns:
            bool: True if the utterance has the given vocabulary it
        """
        lang = lang or self.lang
        cache_key = lang + voc_filename
        if cache_key not in self.voc_match_cache:
            # Check for both skill resources and mycroft-core resources
            voc = self.find_resource(voc_filename + '.voc', 'vocab')
            if not voc:  # Check for vocab in mycroft core resources
                voc = resolve_resource_file(join('text', lang,
                                                 voc_filename + '.voc'))

            if not voc or not exists(voc):
                raise FileNotFoundError(f'Could not find {voc_filename}.voc file')
            # load vocab and flatten into a simple list
            vocab = read_vocab_file(voc)
            self.voc_match_cache[cache_key] = list(chain(*vocab))
        if utt:
            if exact:
                # Check for exact match
                return any(i.strip() == utt
                           for i in self.voc_match_cache[cache_key])
            else:
                # Check for matches against complete words
                return any([re.match(r'.*\b' + i + r'\b.*', utt)
                            for i in self.voc_match_cache[cache_key]])
        else:
            return False

    def report_metric(self, name, data):
        """Report a skill metric to the Mycroft servers.

        Args:
            name (str): Name of metric. Must use only letters and hyphens
            data (dict): JSON dictionary to report. Must be valid JSON
        """
        report_metric(f'{self.skill_id}:{name}', data)

    def send_email(self, title, body):
        """Send an email to the registered user's email.

        Args:
            title (str): Title of email
            body  (str): HTML body of email. This supports
                         simple HTML like bold and italics
        """
        DeviceApi().send_email(title, body, basename(self.root_dir))

    def make_active(self):
        """Bump skill to active_skill list in intent_service.

        This enables converse method to be called even without skill being
        used in last 5 minutes.

        deprecated: use self.activate() instead
        """
        # TODO deprecate, backwards compat
        self.activate()

    def _handle_collect_resting(self, message=None):
        """Handler for collect resting screen messages.

        Sends info on how to trigger this skills resting page.
        """
        self.log.info('Registering resting screen')
        msg = message or Message("")
        message = msg.reply(
            'mycroft.mark2.register_idle',
            data={'name': self.resting_name, 'id': self.skill_id},
            context={"skill_id": self.skill_id}
        )
        self.bus.emit(message)

    def register_resting_screen(self):
        """Registers resting screen from the resting_screen_handler decorator.

        This only allows one screen and if two is registered only one
        will be used.
        """
        for attr_name in get_non_properties(self):
            method = getattr(self, attr_name)
            if hasattr(method, 'resting_handler'):
                self.resting_name = method.resting_handler
                self.log.info(f'Registering resting screen {method} for {self.resting_name}.')

                # Register for handling resting screen
                self.add_event(f'{self.skill_id}.idle', method)
                # Register handler for resting screen collect message
                self.add_event('mycroft.mark2.collect_idle',
                               self._handle_collect_resting)

                # Do a send at load to make sure the skill is registered
                # if reloaded
                self._handle_collect_resting()
                break

    def _register_decorated(self):
        """Register all intent handlers that are decorated with an intent.

        Looks for all functions that have been marked by a decorator
        and read the intent data from them.  The intent handlers aren't the
        only decorators used.  Skip properties as calling getattr on them
        executes the code which may have unintended side-effects
        """
        for attr_name in get_non_properties(self):
            method = getattr(self, attr_name)
            if hasattr(method, 'intents'):
                for intent in getattr(method, 'intents'):
                    self.register_intent(intent, method)

            if hasattr(method, 'intent_files'):
                for intent_file in getattr(method, 'intent_files'):
                    self.register_intent_file(intent_file, method)

    def translate(self, text, data=None):
        """Load a translatable single string resource

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
        if not self.dialog_renderer:
            return ""
        return self.dialog_renderer.render(text, data or {})

    def find_resource(self, res_name, res_dirname=None, lang=None):
        """Find a resource file.

        Searches for the given filename using this scheme:

        1. Search the resource lang directory:

           <skill>/<res_dirname>/<lang>/<res_name>

        2. Search the resource directory:

           <skill>/<res_dirname>/<res_name>

        3. Search the locale lang directory or other subdirectory:

           <skill>/locale/<lang>/<res_name> or

           <skill>/locale/<lang>/.../<res_name>

        Args:
            res_name (string): The resource name to be found
            res_dirname (string, optional): A skill resource directory, such
                                            'dialog', 'vocab', 'regex' or 'ui'.
                                            Defaults to None.
            lang (string, optional): language folder to be used.
                                     Defaults to self.lang.

        Returns:
            string: The full path to the resource file or None if not found
        """
        lang = lang or self.lang
        result = self._find_resource(res_name, lang, res_dirname)
        if not result:
            # when resource not found try fallback to en-us
            LOG.warning(
                f"Skill {self.skill_id} resource '{res_name}' for lang '{lang}' not "
                f"found"
            )
        return result

    def _find_resource(self, res_name, lang, res_dirname=None):
        """Finds a resource by name, lang and dir
        """
        if res_dirname:
            # Try the old translated directory (dialog/vocab/regex)
            lang_path = self._get_language_dir(
                join(self.root_dir, res_dirname), lang)
            path = join(lang_path, res_name)
            if exists(path):
                return path

            # Try old-style non-translated resource
            path = join(self.root_dir, res_dirname, res_name)
            if exists(path):
                return path

        # New scheme:  search for res_name under the 'locale' folder
        root_path = self._get_language_dir(join(self.root_dir, 'locale'), lang)
        for path, _, files in walk(root_path):
            if res_name in files:
                return join(path, res_name)

        # Not found
        return None

    def translate_namedvalues(self, name, delim=','):
        """Load translation dict containing names and values.

        This loads a simple CSV from the 'dialog' folders.
        The name is the first list item, the value is the
        second.  Lines prefixed with # or // get ignored

        Args:
            name (str): name of the .value file, no extension needed
            delim (char): delimiter character used, default is ','

        Returns:
            dict: name and value dictionary, or empty dict if load fails
        """

        if not name.endswith('.value'):
            name += '.value'

        try:
            filename = self.find_resource(name, 'dialog')
            return read_value_file(filename, delim)

        except Exception:
            return {}

    def translate_template(self, template_name, data=None):
        """Load a translatable template.

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
        """Load a list of translatable string resources

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
        filename = self.find_resource(name, 'dialog')
        return read_translated_file(filename, data)

    def add_event(self, name, handler, handler_info=None, once=False):
        """Create event handler for executing intent or other event.

        Args:
            name (string): IntentParser name
            handler (func): Method to call
            handler_info (string): Base message when reporting skill event
                                   handler status on messagebus.
            once (bool, optional): Event handler will be removed after it has
                                   been run once.
        """
        skill_data = {'name': get_handler_name(handler)}

        def on_error(error, message):
            """Speak and log the error."""
            # Convert "MyFancySkill" to "My Fancy Skill" for speaking
            handler_name = camel_case_split(self.name)
            msg_data = {'skill': handler_name}
            speech = dialog.get('skill.error', self.lang, msg_data)
            self.speak(speech)
            LOG.exception(error)
            # append exception information in message
            skill_data['exception'] = repr(error)
            if handler_info:
                # Indicate that the skill handler errored
                msg_type = handler_info + '.error'
                message = message or Message("")
                message.context["skill_id"] = self.skill_id
                self.bus.emit(message.forward(msg_type, skill_data))

        def on_start(message):
            """Indicate that the skill handler is starting."""
            if handler_info:
                # Indicate that the skill handler is starting if requested
                msg_type = handler_info + '.start'
                message.context["skill_id"] = self.skill_id
                self.bus.emit(message.forward(msg_type, skill_data))

        def on_end(message):
            """Store settings and indicate that the skill handler has completed
            """
            if self.settings != self._initial_settings:
                self.settings.store()
                self._initial_settings = copy(self.settings)
            if handler_info:
                msg_type = handler_info + '.complete'
                message.context["skill_id"] = self.skill_id
                self.bus.emit(message.forward(msg_type, skill_data))

        wrapper = create_wrapper(handler, self.skill_id, on_start, on_end,
                                 on_error)
        return self.events.add(name, wrapper, once)

    def remove_event(self, name):
        """Removes an event from bus emitter and events list.

        Args:
            name (string): Name of Intent or Scheduler Event
        Returns:
            bool: True if found and removed, False if not found
        """
        return self.events.remove(name)

    def _register_adapt_intent(self, intent_parser, handler):
        """Register an adapt intent.

        Args:
            intent_parser: Intent object to parse utterance for the handler.
            handler (func): function to register with intent
        """
        # Default to the handler's function name if none given
        name = intent_parser.name or handler.__name__
        munge_intent_parser(intent_parser, name, self.skill_id)
        self.intent_service.register_adapt_intent(name, intent_parser)
        if handler:
            self.add_event(intent_parser.name, handler,
                           'mycroft.skill.handler')

    def register_intent(self, intent_parser, handler):
        """Register an Intent with the intent service.

        Args:
            intent_parser: Intent, IntentBuilder object or padatious intent
                           file to parse utterance for the handler.
            handler (func): function to register with intent
        """
        if isinstance(intent_parser, IntentBuilder):
            intent_parser = intent_parser.build()
        if (isinstance(intent_parser, str) and
                intent_parser.endswith('.intent')):
            return self.register_intent_file(intent_parser, handler)
        elif not isinstance(intent_parser, Intent):
            raise ValueError('"' + str(intent_parser) + '" is not an Intent')

        return self._register_adapt_intent(intent_parser, handler)

    def register_intent_file(self, intent_file, handler):
        """Register an Intent file with the intent service.

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
                         that should activate the intent.  Must end with
                         '.intent'
            handler:     function to register with intent
        """
        langs = [self._core_lang] + self._secondary_langs
        for lang in langs:
            name = f'{self.skill_id}:{intent_file}'
            filename = self.find_resource(intent_file, 'vocab', lang=lang)
            if not filename:
                self.log.error(f'Unable to find "{intent_file}"')
                continue
            self.intent_service.register_padatious_intent(name, filename, lang)
            if handler:
                self.add_event(name, handler, 'mycroft.skill.handler')

    def register_entity_file(self, entity_file):
        """Register an Entity file with the intent service.

        An Entity file lists the exact values that an entity can hold.
        For example:

        === ask.day.intent ===
        Is it {weekend}?

        === weekend.entity ===
        Saturday
        Sunday

        Args:
            entity_file (string): name of file that contains examples of an
                                  entity.  Must end with '.entity'
        """
        if entity_file.endswith('.entity'):
            entity_file = entity_file.replace('.entity', '')
        langs = [self._core_lang] + self._secondary_langs
        for lang in langs:
            filename = self.find_resource(entity_file + ".entity", 'vocab',
                                          lang=lang)
            if not filename:
                self.log.error(f'Unable to find "{entity_file}"')
                continue
            name = f'{self.skill_id}:{entity_file}'
            self.intent_service.register_padatious_entity(name, filename, lang)

    def handle_enable_intent(self, message):
        """Listener to enable a registered intent if it belongs to this skill.
        """
        intent_name = message.data['intent_name']
        for (name, _) in self.intent_service:
            if name == intent_name:
                return self.enable_intent(intent_name)

    def handle_disable_intent(self, message):
        """Listener to disable a registered intent if it belongs to this skill.
        """
        intent_name = message.data['intent_name']
        for (name, _) in self.intent_service:
            if name == intent_name:
                return self.disable_intent(intent_name)

    def disable_intent(self, intent_name):
        """Disable a registered intent if it belongs to this skill.

        Args:
            intent_name (string): name of the intent to be disabled

        Returns:
                bool: True if disabled, False if it wasn't registered
        """
        if intent_name in self.intent_service:
            LOG.info('Disabling intent ' + intent_name)
            name = f'{self.skill_id}:{intent_name}'
            self.intent_service.detach_intent(name)

            langs = [self._core_lang] + self._secondary_langs
            for lang in langs:
                lang_intent_name = f'{name}_{lang}'
                self.intent_service.detach_intent(lang_intent_name)
            return True
        else:
            LOG.error(f'Could not disable {intent_name}, it hasn\'t been registered.')
            return False

    def enable_intent(self, intent_name):
        """(Re)Enable a registered intent if it belongs to this skill.

        Args:
            intent_name: name of the intent to be enabled

        Returns:
            bool: True if enabled, False if it wasn't registered
        """
        intent = self.intent_service.get_intent(intent_name)
        if intent:
            if ".intent" in intent_name:
                self.register_intent_file(intent_name, None)
            else:
                intent.name = intent_name
                self.register_intent(intent, None)
            LOG.debug(f'Enabling intent {intent_name}')
            return True
        else:
            LOG.error(f'Could not enable {intent_name}, it hasn\'t been registered.')
            return False

    def set_context(self, context, word='', origin=''):
        """Add context to intent service

        Args:
            context:    Keyword
            word:       word connected to keyword
            origin:     origin of context
        """
        if not isinstance(context, str):
            raise ValueError('Context should be a string')
        if not isinstance(word, str):
            raise ValueError('Word should be a string')

        context = to_alnum(self.skill_id) + context
        self.intent_service.set_adapt_context(context, word, origin)

    def handle_set_cross_context(self, message):
        """Add global context to intent service."""
        context = message.data.get('context')
        word = message.data.get('word')
        origin = message.data.get('origin')

        self.set_context(context, word, origin)

    def handle_remove_cross_context(self, message):
        """Remove global context from intent service."""
        context = message.data.get('context')
        self.remove_context(context)

    def set_cross_skill_context(self, context, word=''):
        """Tell all skills to add a context to intent service

        Args:
            context:    Keyword
            word:       word connected to keyword
        """
        msg = dig_for_message() or Message("")
        if "skill_id" not in msg.context:
            msg.context["skill_id"] = self.skill_id
        self.bus.emit(msg.forward('mycroft.skill.set_cross_context',
                                  {'context': context, 'word': word,
                                   'origin': self.skill_id}))

    def remove_cross_skill_context(self, context):
        """Tell all skills to remove a keyword from the context manager."""
        if not isinstance(context, str):
            raise ValueError('context should be a string')
        msg = dig_for_message() or Message("")
        if "skill_id" not in msg.context:
            msg.context["skill_id"] = self.skill_id
        self.bus.emit(msg.forward('mycroft.skill.remove_cross_context',
                                  {'context': context}))

    def remove_context(self, context):
        """Remove a keyword from the context manager."""
        if not isinstance(context, str):
            raise ValueError('context should be a string')
        context = to_alnum(self.skill_id) + context
        self.intent_service.remove_adapt_context(context)

    def register_vocabulary(self, entity, entity_type, lang=None):
        """ Register a word to a keyword

        Args:
            entity:         word to register
            entity_type:    Intent handler entity to tie the word to
        """
        keyword_type = to_alnum(self.skill_id) + entity_type
        self.intent_service.register_adapt_keyword(keyword_type, entity, lang=lang or self.lang)

    def register_regex(self, regex_str, lang=None):
        """Register a new regex.
        Args:
            regex_str: Regex string
        """
        self.log.debug('registering regex string: ' + regex_str)
        regex = munge_regex(regex_str, self.skill_id)
        re.compile(regex)  # validate regex
        self.intent_service.register_adapt_regex(regex, lang=lang or self.lang)

    def speak(self, utterance, expect_response=False, wait=False, meta=None):
        """Speak a sentence.

        Args:
            utterance (str):        sentence mycroft should speak
            expect_response (bool): set to True if Mycroft should listen
                                    for a response immediately after
                                    speaking the utterance.
            wait (bool):            set to True to block while the text
                                    is being spoken.
            meta:                   Information of what built the sentence.
        """
        # registers the skill as being active
        meta = meta or {}
        meta['skill'] = self.skill_id
        self.enclosure.register(self.skill_id)
        data = {'utterance': utterance,
                'expect_response': expect_response,
                'meta': meta,
                'lang': self.lang}
        message = dig_for_message()
        m = message.forward("speak", data) if message \
            else Message("speak", data)
        m.context["skill_id"] = self.skill_id
        self.bus.emit(m)

        if wait:
            wait_while_speaking()

    def speak_dialog(self, key, data=None, expect_response=False, wait=False):
        """ Speak a random sentence from a dialog file.

        Args:
            key (str): dialog file key (e.g. "hello" to speak from the file
                                        "locale/en-us/hello.dialog")
            data (dict): information used to populate sentence
            expect_response (bool): set to True if Mycroft should listen
                                    for a response immediately after
                                    speaking the utterance.
            wait (bool):            set to True to block while the text
                                    is being spoken.
        """
        if self.dialog_renderer:
            data = data or {}
            self.speak(
                self.dialog_renderer.render(key, data),
                expect_response, wait, meta={'dialog': key, 'data': data}
            )
        else:
            self.log.warning(
                'dialog_render is None, does the locale/dialog folder exist?'
            )
            self.speak(key, expect_response, wait, {})

    def acknowledge(self):
        """Acknowledge a successful request.

        This method plays a sound to acknowledge a request that does not
        require a verbal response. This is intended to provide simple feedback
        to the user that their request was handled successfully.
        """
        audio_file = resolve_resource_file(
            self.config_core.get('sounds').get('acknowledge'))

        if not audio_file:
            LOG.warning("Could not find 'acknowledge' audio file!")
            return

        process = play_audio_file(audio_file)
        if not process:
            LOG.warning("Unable to play 'acknowledge' audio file!")

    def _load_dialog_files(self, root_directory, lang):
        # If "<skill>/dialog/<lang>" exists, load from there.  Otherwise
        # load dialog from "<skill>/locale/<lang>"
        dialog_dir = self._get_language_dir(
            join(root_directory, 'dialog'), lang)
        locale_dir = self._get_language_dir(
            join(root_directory, 'locale'), lang)
        if exists(dialog_dir):
            self.dialog_renderers[lang] = load_dialogs(dialog_dir)
        elif exists(locale_dir):
            self.dialog_renderers[lang] = load_dialogs(locale_dir)
        else:
            LOG.debug(f'No dialog loaded for {lang}')

    def init_dialog(self, root_directory):
        langs = [self._core_lang] + self._secondary_langs
        for lang in langs:
            self._load_dialog_files(root_directory, lang)

    def load_data_files(self, root_directory=None):
        """Called by the skill loader to load intents, dialogs, etc.

        Args:
            root_directory (str): root folder to use when loading files.
        """
        root_directory = root_directory or self.root_dir
        self.init_dialog(root_directory)
        self.load_vocab_files(root_directory)
        self.load_regex_files(root_directory)

    def _load_vocab_files(self, root_directory, lang):
        keywords = []
        vocab_dir = self._get_language_dir(join(root_directory, 'vocab'), lang)
        locale_dir = self._get_language_dir(join(root_directory, 'locale'),
                                            lang)

        if exists(vocab_dir):
            keywords = load_vocabulary(vocab_dir, self.skill_id)
        elif exists(locale_dir):
            keywords = load_vocabulary(locale_dir, self.skill_id)
        else:
            LOG.debug(f'No vocab loaded for {lang}')

        # For each found intent register the default along with any aliases
        for vocab_type in keywords:
            for line in keywords[vocab_type]:
                entity = line[0]
                aliases = line[1:]
                self.intent_service.register_adapt_keyword(vocab_type,
                                                           entity,
                                                           aliases,
                                                           lang)

    def load_vocab_files(self, root_directory):
        """ Load vocab files found under root_directory.

        Args:
            root_directory (str): root folder to use when loading files
        """
        langs = [self._core_lang] + self._secondary_langs
        for lang in langs:
            self._load_vocab_files(root_directory, lang)

    def _load_regex_files(self, root_directory, lang):
        """ Load regex files found under the skill directory.

        Args:
            root_directory (str): root folder to use when loading files
        """
        regexes = []
        regex_dir = self._get_language_dir(join(root_directory, 'regex'), lang)
        locale_dir = self._get_language_dir(join(root_directory, 'locale'), lang)

        if exists(regex_dir):
            regexes = load_regex(regex_dir, self.skill_id)
        elif exists(locale_dir):
            regexes = load_regex(locale_dir, self.skill_id)

        for regex in regexes:
            self.intent_service.register_adapt_regex(regex, lang)

    def load_regex_files(self, root_directory):
        """ Load regex files found under the skill directory.

        Args:
            root_directory (str): root folder to use when loading files
        """
        langs = [self._core_lang] + self._secondary_langs
        for lang in langs:
            self._load_regex_files(root_directory, lang)

    def __handle_stop(self, message):
        """Handler for the "mycroft.stop" signal. Runs the user defined
        `stop()` method.
        """
        try:
            if self.stop():
                self.bus.emit(message.reply("mycroft.stop.handled",
                                            {"by": "skill:" + self.skill_id},
                                            {"skill_id": self.skill_id}))
        except Exception as e:
            LOG.exception(e)
            LOG.error(f'Failed to stop skill: {self.skill_id}')

    def stop(self):
        """Optional method implemented by subclass."""
        pass

    def shutdown(self):
        """Optional shutdown proceedure implemented by subclass.

        This method is intended to be called during the skill process
        termination. The skill implementation must shutdown all processes and
        operations in execution.
        """
        pass

    def default_shutdown(self):
        """Parent function called internally to shut down everything.

        Shuts down known entities and calls skill specific shutdown method.
        """
        self.settings_change_callback = None

        # Store settings
        if self.settings != self._initial_settings:
            self.settings.store()
        if self.settings_meta:
            self.settings_meta.stop()

        # Clear skill from gui
        self.gui.shutdown()

        # removing events
        self.event_scheduler.shutdown()
        self.events.clear()

        try:
            self.stop()
        except Exception:
            LOG.error(f'Failed to stop skill: {self.skill_id}', exc_info=True)

        try:
            self.shutdown()
        except Exception as e:
            LOG.error(f'Skill specific shutdown function encountered an error: {e}')

        self.bus.emit(
            Message('detach_skill', {'skill_id': str(self.skill_id) + ':'},
                    {"skill_id": self.skill_id}))

    def schedule_event(self, handler, when, data=None, name=None,
                       context=None):
        """Schedule a single-shot event.

        Args:
            handler:               method to be called
            when (datetime/int/float):   datetime (in system timezone) or
                                   number of seconds in the future when the
                                   handler should be called
            data (dict, optional): data to send when the handler is called
            name (str, optional):  reference name
                                   NOTE: This will not warn or replace a
                                   previously scheduled event of the same
                                   name.
            context (dict, optional): context (dict, optional): message
                                      context to send when the handler
                                      is called
        """
        message = dig_for_message()
        context = context or message.context if message else {}
        context["skill_id"] = self.skill_id
        return self.event_scheduler.schedule_event(handler, when, data, name,
                                                   context=context)

    def schedule_repeating_event(self, handler, when, frequency,
                                 data=None, name=None, context=None):
        """Schedule a repeating event.

        Args:
            handler:                method to be called
            when (datetime):        time (in system timezone) for first
                                    calling the handler, or None to
                                    initially trigger <frequency> seconds
                                    from now
            frequency (float/int):  time in seconds between calls
            data (dict, optional):  data to send when the handler is called
            name (str, optional):   reference name, must be unique
            context (dict, optional): context (dict, optional): message
                                      context to send when the handler
                                      is called
        """
        message = dig_for_message()
        context = context or message.context if message else {}
        context["skill_id"] = self.skill_id
        return self.event_scheduler.schedule_repeating_event(
            handler,
            when,
            frequency,
            data,
            name,
            context=context
        )

    def update_scheduled_event(self, name, data=None):
        """Change data of event.

        Args:
            name (str): reference name of event (from original scheduling)
            data (dict): event data
        """
        return self.event_scheduler.update_scheduled_event(name, data)

    def cancel_scheduled_event(self, name):
        """Cancel a pending event. The event will no longer be scheduled
        to be executed

        Args:
            name (str): reference name of event (from original scheduling)
        """
        return self.event_scheduler.cancel_scheduled_event(name)

    def get_scheduled_event_status(self, name):
        """Get scheduled event data and return the amount of time left

        Args:
            name (str): reference name of event (from original scheduling)

        Returns:
            int: the time left in seconds

        Raises:
            Exception: Raised if event is not found
        """
        return self.event_scheduler.get_scheduled_event_status(name)

    def cancel_all_repeating_events(self):
        """Cancel any repeating events started by the skill."""
        return self.event_scheduler.cancel_all_repeating_events()
