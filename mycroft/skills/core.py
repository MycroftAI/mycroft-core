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
import collections
import operator
import sys
import time
import csv
import inspect
import os
import traceback
from inspect import signature
from datetime import datetime, timedelta

import abc
import re
from adapt.intent import Intent, IntentBuilder
from os.path import join, abspath, dirname, basename, exists
from threading import Event, Timer

from mycroft import dialog
from mycroft.api import DeviceApi
from mycroft.audio import wait_while_speaking
from mycroft.enclosure.api import EnclosureAPI
from mycroft.configuration import Configuration
from mycroft.dialog import DialogLoader
from mycroft.filesystem import FileSystemAccess
from mycroft.messagebus.message import Message
from mycroft.metrics import report_metric, report_timing, Stopwatch
from mycroft.skills.settings import SkillSettings
from mycroft.skills.skill_data import (load_vocabulary, load_regex, to_alnum,
                                       munge_regex, munge_intent_parser)
from mycroft.util import camel_case_split, resolve_resource_file
from mycroft.util.log import LOG

MainModule = '__init__'


def simple_trace(stack_trace):
    stack_trace = stack_trace[:-1]
    tb = "Traceback:\n"
    for line in stack_trace:
        if line.strip():
            tb += line
    return tb


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
    """ Restore message keywords by removing the Letterified skill ID.

    Args:
        message (Message): Intent result message
        skill_id (str): skill identifier

    Returns:
        Message without clear keywords
    """
    if isinstance(message, Message) and isinstance(message.data, dict):
        skill_id = to_alnum(skill_id)
        for key in list(message.data.keys()):
            if key.startswith(skill_id):
                # replace the munged key with the real one
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


def load_skill(skill_descriptor, bus, skill_id, BLACKLISTED_SKILLS=None):
    """ Load skill from skill descriptor.

    Args:
        skill_descriptor: descriptor of skill to load
        bus:              Mycroft messagebus connection
        skill_id:         id number for skill

    Returns:
        MycroftSkill: the loaded skill or None on failure
    """
    BLACKLISTED_SKILLS = BLACKLISTED_SKILLS or []
    path = skill_descriptor["path"]
    name = basename(path)
    LOG.info("ATTEMPTING TO LOAD SKILL: {} with ID {}".format(name, skill_id))
    if name in BLACKLISTED_SKILLS:
        LOG.info("SKILL IS BLACKLISTED " + name)
        return None
    main_file = join(path, MainModule + '.py')
    try:
        with open(main_file, 'rb') as fp:
            skill_module = imp.load_module(name.replace('.', '_'), fp,
                                           main_file, ('.py', 'rb',
                                           imp.PY_SOURCE))
        if (hasattr(skill_module, 'create_skill') and
                callable(skill_module.create_skill)):
            # v2 skills framework
            skill = skill_module.create_skill()
            skill.skill_id = skill_id
            skill.settings.allow_overwrite = True
            skill.settings.load_skill_settings_from_file()
            skill.bind(bus)
            try:
                skill.load_data_files(path)
                # Set up intent handlers
                skill._register_decorated()
                skill.register_resting_screen()
                skill.initialize()
            except Exception as e:
                # If an exception occurs, make sure to clean up the skill
                skill.default_shutdown()
                raise e

            LOG.info("Loaded " + name)
            # The very first time a skill is run, speak the intro
            first_run = skill.settings.get("__mycroft_skill_firstrun", True)
            if first_run:
                LOG.info("First run of " + name)
                skill.settings["__mycroft_skill_firstrun"] = False
                skill.settings.store()
                intro = skill.get_intro_message()
                if intro:
                    skill.speak(intro)
            return skill
        else:
            LOG.warning("Module {} does not appear to be skill".format(name))
    except FileNotFoundError as e:
        LOG.error(
            'Failed to load {} due to a missing file: {}'.format(name, str(e))
            )
    except Exception:
        LOG.exception("Failed to load skill: " + name)
    return None


def create_skill_descriptor(skill_path):
    return {"path": skill_path}


def get_handler_name(handler):
    """ Name (including class if available) of handler function.

    Args:
        handler (function): Function to be named

    Returns:
        string: handler name as string
    """
    if '__self__' in dir(handler) and 'name' in dir(handler.__self__):
        return handler.__self__.name + '.' + handler.__name__
    else:
        return handler.__name__


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


class SkillGUI:
    """
    SkillGUI - Interface to the Graphical User Interface

    Values set in this class are synced to the GUI, accessible within QML
    via the built-in sessionData mechanism.  For example, in Python you can
    write in a skill:
        self.gui['temp'] = 33
        self.gui.show_page('Weather.qml')
    Then in the Weather.qml you'd access the temp via code such as:
        text: sessionData.time
    """

    def __init__(self, skill):
        self.__session_data = {}  # synced to GUI for use by this skill's pages
        self.page = None    # the active GUI page (e.g. QML template) to show
        self.skill = skill
        self.on_gui_changed_callback = None

    def build_message_type(self, event):
        """ Builds a message matching the output from the enclosure. """
        return '{}.{}'.format(self.skill.skill_id, event)

    def setup_default_handlers(self):
        """ Sets the handlers for the default messages. """
        msg_type = self.build_message_type('set')
        print("LISTENING FOR {}".format(msg_type))
        self.skill.add_event(msg_type, self.gui_set)

    def register_handler(self, event, handler):
        """ Register a handler for gui events.

            when using the triggerEvent method from Qt
            triggerEvent("event", {"data": "cool"})

            Arguments:
                event (str):    event to catch
                handler:        function to handle the event
        """
        msg_type = self.build_message_type(event)
        self.skill.add_event(msg_type, handler)

    def set_on_gui_changed(self, callback):
        """ Registers a callback function to run when a value is
            changed from the GUI.

            Arguments:
                callback:   Function to call when a value is changed
        """
        self.on_gui_changed_callback = callback

    def gui_set(self, message):
        for key in message.data:
            print("SETTING {} TO {}".format(key, message.data[key]))
            self[key] = message.data[key]
        if self.on_gui_changed_callback:
            self.on_gui_changed_callback()

    def __setitem__(self, key, value):
        self.__session_data[key] = value

        if self.page:
            # emit notification (but not needed if page has not been shown yet)
            data = self.__session_data.copy()
            data.update({'__from': self.skill.skill_id})
            self.skill.bus.emit(Message("gui.value.set", data))

    def __getitem__(self, key):
        return self.__session_data[key]

    def __contains__(self, key):
        return self.__session_data.__contains__(key)

    def clear(self):
        """ Reset the value dictionary """
        self.__session_data = {}
        self.page = None

    def show_page(self, name, override_idle=None):
        """
        Begin showing the page in the GUI

        Args:
            name (str): Name of page (e.g "mypage.qml") to display
            override_idle: If set will override the idle screen
        """
        self.show_pages([name], 0, override_idle)

    def show_pages(self, page_names, index=0, override_idle=None):
        """
        Begin showing the list of pages in the GUI

        Args:
            page_names (list): List of page names (str) to display, such as
                               ["Weather.qml", "Forecast.qml", "Details.qml"]
            index (int): Page number (0-based) to show initially.  For the
                         above list a value of 1 would start on "Forecast.qml"
            override_idle: If set will override the idle screen
        """
        if not isinstance(page_names, list):
            raise ValueError('page_names must be a list')

        if index > len(page_names):
            raise ValueError('Default index is larger than page list length')

        self.page = page_names[index]

        # First sync any data...
        data = self.__session_data.copy()
        data.update({'__from': self.skill.skill_id})
        self.skill.bus.emit(Message("gui.value.set", data))

        # Convert pages to full reference
        page_urls = []
        for name in page_names:
            page = self.skill.find_resource(name, 'ui')
            if page:
                page_urls.append("file://" + page)
            else:
                raise FileNotFoundError("Unable to find page: {}".format(name))

        self.skill.bus.emit(Message("gui.page.show",
                                    {"page": page_urls,
                                     "index": index,
                                     "__from": self.skill.skill_id,
                                     "__idle": override_idle}))

    def show_text(self, text, title=None):
        """ Display a GUI page for viewing simple text

        Arguments:
            text (str): Main text content.  It will auto-paginate
            title (str): A title to display above the text content.
        """
        self.clear()
        self["text"] = text
        self["title"] = title
        self.show_page("SYSTEM_TEXTFRAME")

    def show_image(self, url, caption=None, title=None):
        """ Display a GUI page for viewing an image

        Arguments:
            url (str): Pointer to the image
            caption (str): A caption to show under the image
            title (str): A title to display above the image content
        """
        self.clear()
        self["image"] = url
        self["title"] = title
        self["caption"] = caption
        self.show_page("SYSTEM_IMAGEFRAME")

    def show_html(self, html):
        """ Display an HTML page in the GUI

        Arguments:
            html (str): HTML text to display
        """
        self.clear()
        self["url"] = ""  # TODO: Save to a temp file... html
        self.show_page("SYSTEM_HTMLFRAME")

    def show_url(self, url):
        """ Display an HTML page in the GUI

        Arguments:
            url (str): URL to render
        """
        self.clear()
        self["url"] = url
        self.show_page("SYSTEM_HTMLFRAME")


def resting_screen_handler(name=None):
    """ Decorator for adding a method as an resting screen handler.

        If selected will be shown on screen when device enters idle mode
    """
    name = name or func.__self__.name

    def real_decorator(func):
        # Store the resting information inside the function
        # This will be used later in register_resting_screen
        if not hasattr(func, 'resting_handler'):
            func.resting_handler = name
        return func

    return real_decorator


#######################################################################
# MycroftSkill base class
#######################################################################
class MycroftSkill:
    """
    Abstract base class which provides common behaviour and parameters to all
    Skills implementation.
    """

    def __init__(self, name=None, bus=None):
        self.name = name or self.__class__.__name__
        self.resting_name = None
        # Get directory of skill
        self._dir = dirname(abspath(sys.modules[self.__module__].__file__))
        self.settings = SkillSettings(self._dir, self.name)

        self.gui = SkillGUI(self)

        self._bus = None
        self._enclosure = None
        self.bind(bus)
        #: Mycroft global configuration. (dict)
        self.config_core = Configuration.get()
        self.config = self.config_core.get(self.name) or {}
        self.dialog_renderer = None
        self.root_dir = None  #: skill root directory

        #: Filesystem access to skill specific folder.
        #: See mycroft.filesystem for details.
        self.file_system = FileSystemAccess(join('skills', self.name))
        self.registered_intents = []
        self.log = LOG.create_logger(self.name)  #: Skill logger instance
        self.reload_skill = True  #: allow reloading (default True)
        self.events = []
        self.scheduled_repeats = []
        self.skill_id = ''  # will be set from the path, so guaranteed unique
        self.voc_match_cache = {}

    @property
    def enclosure(self):
        if self._enclosure:
            return self._enclosure
        else:
            LOG.error("Skill not fully initialized. Move code " +
                      "from  __init__() to initialize() to correct this.")
            LOG.error(simple_trace(traceback.format_stack()))
            raise Exception("Accessed MycroftSkill.enclosure in __init__")

    @property
    def bus(self):
        if self._bus:
            return self._bus
        else:
            LOG.error("Skill not fully initialized. Move code " +
                      "from __init__() to initialize() to correct this.")
            LOG.error(simple_trace(traceback.format_stack()))
            raise Exception("Accessed MycroftSkill.bus in __init__")

    @property
    def emitter(self):
        """ Backwards compatibility. This is the same as self.bus.
        TODO: Remove in 19.02
        """
        self.log.warning('self.emitter is deprecated switch to "self.bus"')
        return self._bus

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

    def bind(self, bus):
        """ Register messagebus emitter with skill.

        Arguments:
            bus: Mycroft messagebus connection
        """
        if bus:
            self._bus = bus
            self._enclosure = EnclosureAPI(bus, self.name)
            self.add_event('mycroft.stop', self.__handle_stop)
            self.add_event('mycroft.skill.enable_intent',
                           self.handle_enable_intent)
            self.add_event('mycroft.skill.disable_intent',
                           self.handle_disable_intent)
            self.add_event("mycroft.skill.set_cross_context",
                           self.handle_set_cross_context)
            self.add_event("mycroft.skill.remove_cross_context",
                           self.handle_remove_cross_context)
            name = 'mycroft.skills.settings.update'
            func = self.settings.run_poll
            bus.on(name, func)
            self.events.append((name, func))

            # Intialize the SkillGui
            self.gui.setup_default_handlers()

    def detach(self):
        for (name, intent) in self.registered_intents:
            name = str(self.skill_id) + ':' + name
            self.bus.emit(Message("detach_intent", {"intent_name": name}))

    def initialize(self):
        """ Perform any final setup needed for the skill.

        Invoked after the skill is fully constructed and registered with the
        system.
        """
        pass

    def get_intro_message(self):
        """ Get a message to speak on first load of the skill.

        Useful for post-install setup instructions.

        Returns:
            str: message that will be spoken to the user
        """
        return None

    def converse(self, utterances, lang="en-us"):
        """ Handle conversation.

        This method gets a peek at utterances before the normal intent
        handling process after a skill has been invoked once.

        To use, override the converse() method and return True to
        indicate that the utterance has been handled.

        Args:
            utterances (list): The utterances from the user
            lang:       language the utterance is in

        Returns:
            bool: True if an utterance was handled, otherwise False
        """
        return False

    def __get_response(self):
        """ Helper to get a reponse from the user

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

    def get_response(self, dialog='', data=None, validator=None,
                     on_fail=None, num_retries=-1):
        """
        Prompt user and wait for response

        The given dialog is spoken, followed immediately by listening
        for a user response.  The response can optionally be
        validated before returning.

        Example:
            color = self.get_response('ask.favorite.color')

        Args:
            dialog (str): Announcement dialog to speak to the user
            data (dict): Data used to render the dialog
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
            return self.dialog_renderer.render(dialog, data)

        if not get_announcement():
            raise ValueError('dialog message required')

        def on_fail_default(utterance):
            fail_data = data.copy()
            fail_data['utterance'] = utterance
            if on_fail:
                return self.dialog_renderer.render(on_fail, fail_data)
            else:
                return get_announcement()

        def is_cancel(utterance):
            return self.voc_match(utterance, 'cancel')

        def validator_default(utterance):
            # accept anything except 'cancel'
            return not is_cancel(utterance)

        validator = validator or validator_default
        on_fail_fn = on_fail if callable(on_fail) else on_fail_default

        self.speak(get_announcement(), expect_response=True, wait=True)
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

    def ask_yesno(self, prompt, data=None):
        """ Read prompt and wait for a yes/no answer

        This automatically deals with translation and common variants,
        such as 'yeah', 'sure', etc.

        Args:
              prompt (str): a dialog id or string to read
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

    def voc_match(self, utt, voc_filename, lang=None):
        """ Determine if the given utterance contains the vocabulary provided

        Checks for vocabulary match in the utterance instead of the other
        way around to allow the user to say things like "yes, please" and
        still match against "Yes.voc" containing only "yes". The method first
        checks in the current skill's .voc files and secondly the "res/text"
        folder of mycroft-core. The result is cached to avoid hitting the
        disk each time the method is called.

        Args:
            utt (str): Utterance to be tested
            voc_filename (str): Name of vocabulary file (e.g. 'yes' for
                                'res/text/en-us/yes.voc')
            lang (str): Language code, defaults to self.long

        Returns:
            bool: True if the utterance has the given vocabulary it
        """
        lang = lang or self.lang
        cache_key = lang + voc_filename
        if cache_key not in self.voc_match_cache:
            # Check for both skill resources and mycroft-core resources
            voc = self.find_resource(voc_filename + '.voc', 'vocab')
            if not voc:
                voc = resolve_resource_file(join('text', lang,
                                                 voc_filename + '.voc'))

            if not voc or not exists(voc):
                raise FileNotFoundError(
                        'Could not find {}.voc file'.format(voc_filename))

            with open(voc) as f:
                self.voc_match_cache[cache_key] = f.read().splitlines()

        # Check for match
        if utt and any(i.strip() in utt
                       for i in self.voc_match_cache[cache_key]):
            return True
        return False

    def report_metric(self, name, data):
        """ Report a skill metric to the Mycroft servers

        Args:
            name (str): Name of metric. Must use only letters and hyphens
            data (dict): JSON dictionary to report. Must be valid JSON
        """
        report_metric(basename(self.root_dir) + ':' + name, data)

    def send_email(self, title, body):
        """ Send an email to the registered user's email

        Args:
            title (str): Title of email
            body  (str): HTML body of email. This supports
                         simple HTML like bold and italics
        """
        DeviceApi().send_email(title, body, basename(self.root_dir))

    def make_active(self):
        """ Bump skill to active_skill list in intent_service

        This enables converse method to be called even without skill being
        used in last 5 minutes.
        """
        self.bus.emit(Message('active_skill_request',
                              {"skill_id": self.skill_id}))

    def _handle_collect_resting(self, message=None):
        """ Handler for collect resting screen messages.

            Sends info on how to trigger this skills resting page.
        """
        self.log.info('Registering resting screen')
        self.bus.emit(Message('mycroft.mark2.register_idle',
                              data={'name': self.resting_name,
                                    'id': self.skill_id}))

    def register_resting_screen(self):
        """ Registers resting screen from the resting_screen_handler decorator.

            This only allows one screen and if two is registered only one
            will be used.
        """
        attributes = [a for a in dir(self) if a != 'emitter']
        for attr_name in attributes:
            method = getattr(self, attr_name)

            if hasattr(method, 'resting_handler'):
                self.resting_name = method.resting_handler
                self.log.info('Registering resting screen {} for {}.'.format(
                              method, self.resting_name))

                # Register for handling resting screen
                msg_type = '{}.{}'.format(self.skill_id, 'idle')
                self.add_event(msg_type, method)
                # Register handler for resting screen collect message
                self.add_event('mycroft.mark2.collect_idle',
                               self._handle_collect_resting)

                # Do a send at load to make sure the skill is registered
                # if reloaded
                self._handle_collect_resting()
                return

    def _register_decorated(self):
        """ Register all intent handlers that are decorated with an intent.

        Looks for all functions that have been marked by a decorator
        and read the intent data from them
        """
        attributes = [a for a in dir(self) if not a == 'emitter']
        for attr_name in attributes:
            method = getattr(self, attr_name)

            if hasattr(method, 'intents'):
                for intent in getattr(method, 'intents'):
                    self.register_intent(intent, method)

            if hasattr(method, 'intent_files'):
                for intent_file in getattr(method, 'intent_files'):
                    self.register_intent_file(intent_file, method)

    def translate(self, text, data=None):
        """ Load a translatable single string resource

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

    def find_resource(self, res_name, res_dirname=None):
        """ Find a resource file

        Searches for the given filename using this scheme:
        1) Search the resource lang directory:
             <skill>/<res_dirname>/<lang>/<res_name>
        2) Search the resource directory:
             <skill>/<res_dirname>/<res_name>
        3) Search the locale lang directory or other subdirectory:
             <skill>/locale/<lang>/<res_name> or
             <skill>/locale/<lang>/.../<res_name>

        Args:
            res_name (string): The resource name to be found
            res_dirname (string, optional): A skill resource directory, such
                                            'dialog', 'vocab', 'regex' or 'ui'.
                                            Defaults to None.

        Returns:
            string: The full path to the resource file or None if not found
        """
        if res_dirname:
            # Try the old translated directory (dialog/vocab/regex)
            path = join(self.root_dir, res_dirname, self.lang, res_name)
            if exists(path):
                return path

            # Try old-style non-translated resource
            path = join(self.root_dir, res_dirname, res_name)
            if exists(path):
                return path

        # New scheme:  search for res_name under the 'locale' folder
        root_path = join(self.root_dir, 'locale', self.lang)
        for path, _, files in os.walk(root_path):
            if res_name in files:
                return join(path, res_name)

        # Not found
        return None

    def translate_namedvalues(self, name, delim=None):
        """ Load translation dict containing names and values.

        This loads a simple CSV from the 'dialog' folders.
        The name is the first list item, the value is the
        second.  Lines prefixed with # or // get ignored

        Args:
            name (str): name of the .value file, no extension needed
            delim (char): delimiter character used, default is ','

        Returns:
            dict: name and value dictionary, or empty dict if load fails
        """

        delim = delim or ','
        result = collections.OrderedDict()
        if not name.endswith(".value"):
            name += ".value"

        try:
            filename = self.find_resource(name, 'dialog')
            if filename:
                with open(filename) as f:
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
        """ Load a translatable template

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
        """ Load a list of translatable string resources

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
        if filename:
            with open(filename) as f:
                text = f.read().replace('{{', '{').replace('}}', '}')
                return text.format(**data or {}).rstrip('\n').split('\n')
        else:
            return None

    def add_event(self, name, handler, handler_info=None, once=False):
        """ Create event handler for executing intent

        Args:
            name (string): IntentParser name
            handler (func): Method to call
            handler_info (string): Base message when reporting skill event
                                   handler status on messagebus.
            once (bool, optional): Event handler will be removed after it has
                                   been run once.
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
                    self.bus.emit(message.reply(msg_type, skill_data))

                if once:
                    # Remove registered one-time handler before invoking,
                    # allowing them to re-schedule themselves.
                    self.remove_event(name)

                with stopwatch:
                    if len(signature(handler).parameters) == 0:
                        handler()
                    else:
                        handler(message)
                    self.settings.store()  # Store settings if they've changed

            except Exception as e:
                # Convert "MyFancySkill" to "My Fancy Skill" for speaking
                handler_name = camel_case_split(self.name)
                msg_data = {'skill': handler_name}
                msg = dialog.get('skill.error', self.lang, msg_data)
                self.speak(msg)
                LOG.exception(msg)
                # append exception information in message
                skill_data['exception'] = repr(e)
            finally:
                # Indicate that the skill handler has completed
                if handler_info:
                    msg_type = handler_info + '.complete'
                    self.bus.emit(message.reply(msg_type, skill_data))

                # Send timing metrics
                context = message.context
                if context and 'ident' in context:
                    report_timing(context['ident'], 'skill_handler', stopwatch,
                                  {'handler': handler.__name__})

        if handler:
            if once:
                self.bus.once(name, wrapper)
            else:
                self.bus.on(name, wrapper)
            self.events.append((name, wrapper))

    def remove_event(self, name):
        """ Removes an event from bus emitter and events list

        Args:
            name (string): Name of Intent or Scheduler Event
        Returns:
            bool: True if found and removed, False if not found
        """
        removed = False
        for _name, _handler in list(self.events):
            if name == _name:
                try:
                    self.events.remove((_name, _handler))
                except ValueError:
                    pass
                removed = True

        # Because of function wrappers, the emitter doesn't always directly
        # hold the _handler function, it sometimes holds something like
        # 'wrapper(_handler)'.  So a call like:
        #     self.bus.remove(_name, _handler)
        # will not find it, leaving an event handler with that name left behind
        # waiting to fire if it is ever re-installed and triggered.
        # Remove all handlers with the given name, regardless of handler.
        if removed:
            self.bus.remove_all_listeners(name)
        return removed

    def register_intent(self, intent_parser, handler):
        """ Register an Intent with the intent service.

        Args:
            intent_parser: Intent or IntentBuilder object to parse
                           utterance for the handler.
            handler (func): function to register with intent
        """
        if isinstance(intent_parser, IntentBuilder):
            intent_parser = intent_parser.build()
        elif not isinstance(intent_parser, Intent):
            raise ValueError('"' + str(intent_parser) + '" is not an Intent')

        # Default to the handler's function name if none given
        name = intent_parser.name or handler.__name__
        munge_intent_parser(intent_parser, name, self.skill_id)
        self.bus.emit(Message("register_intent", intent_parser.__dict__))
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
                             that should activate the intent.  Must end with
                             '.intent'
                handler:     function to register with intent
        """
        name = str(self.skill_id) + ':' + intent_file

        filename = self.find_resource(intent_file, 'vocab')
        if not filename:
            raise FileNotFoundError(
                'Unable to find "' + str(intent_file) + '"'
                )

        data = {
            "file_name": filename,
            "name": name
        }
        self.bus.emit(Message("padatious:register_intent", data))
        self.registered_intents.append((intent_file, data))
        self.add_event(name, handler, 'mycroft.skill.handler')

    def register_entity_file(self, entity_file):
        """ Register an Entity file with the intent service.

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

        filename = self.find_resource(entity_file + ".entity", 'vocab')
        if not filename:
            raise FileNotFoundError(
                'Unable to find "' + entity_file + '.entity"'
                )
        name = str(self.skill_id) + ':' + entity_file

        self.bus.emit(Message("padatious:register_entity", {
            "file_name": filename,
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
            intent_name (string): name of the intent to be disabled

        Returns:
                bool: True if disabled, False if it wasn't registered
        """
        names = [intent_tuple[0] for intent_tuple in self.registered_intents]
        if intent_name in names:
            LOG.debug('Disabling intent ' + intent_name)
            name = str(self.skill_id) + ':' + intent_name
            self.bus.emit(Message("detach_intent", {"intent_name": name}))
            return True

        LOG.error('Could not disable ' + intent_name +
                  ', it hasn\'t been registered.')
        return False

    def enable_intent(self, intent_name):
        """
        (Re)Enable a registered intent if it belongs to this skill

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
            if ".intent" in intent_name:
                self.register_intent_file(intent_name, None)
            else:
                intent.name = intent_name
                self.register_intent(intent, None)
            LOG.debug('Enabling intent ' + intent_name)
            return True

        LOG.error('Could not enable ' + intent_name + ', it hasn\'t been '
                                                      'registered.')
        return False

    def set_context(self, context, word='', origin=None):
        """
            Add context to intent service

            Args:
                context:    Keyword
                word:       word connected to keyword
        """
        if not isinstance(context, str):
            raise ValueError('context should be a string')
        if not isinstance(word, str):
            raise ValueError('word should be a string')

        origin = origin or ''
        context = to_alnum(self.skill_id) + context
        self.bus.emit(Message('add_context',
                              {'context': context, 'word': word,
                               'origin': origin}))

    def handle_set_cross_context(self, message):
        """
            Add global context to intent service

        """
        context = message.data.get("context")
        word = message.data.get("word")
        origin = message.data.get("origin")

        self.set_context(context, word, origin)

    def handle_remove_cross_context(self, message):
        """
            Remove global context from intent service

        """
        context = message.data.get("context")
        self.remove_context(context)

    def set_cross_skill_context(self, context, word=''):
        """
            Tell all skills to add a context to intent service

            Args:
                context:    Keyword
                word:       word connected to keyword
        """
        self.bus.emit(Message("mycroft.skill.set_cross_context",
                              {"context": context, "word": word,
                               "origin": self.skill_id}))

    def remove_cross_skill_context(self, context):
        """
           tell all skills to remove a keyword from the context manager.
        """
        if not isinstance(context, str):
            raise ValueError('context should be a string')
        self.bus.emit(Message("mycroft.skill.remove_cross_context",
                              {"context": context}))

    def remove_context(self, context):
        """
            remove a keyword from the context manager.
        """
        if not isinstance(context, str):
            raise ValueError('context should be a string')
        context = to_alnum(self.skill_id) + context
        self.bus.emit(Message('remove_context', {'context': context}))

    def register_vocabulary(self, entity, entity_type):
        """ Register a word to a keyword

            Args:
                entity:         word to register
                entity_type:    Intent handler entity to tie the word to
        """
        self.bus.emit(Message('register_vocab', {
            'start': entity, 'end': to_alnum(self.skill_id) + entity_type
        }))

    def register_regex(self, regex_str):
        """ Register a new regex.
            Args:
                regex_str: Regex string
        """
        regex = munge_regex(regex_str, self.skill_id)
        re.compile(regex)  # validate regex
        self.bus.emit(Message('register_vocab', {'regex': regex}))

    def speak(self, utterance, expect_response=False, wait=False):
        """ Speak a sentence.

            Args:
                utterance (str):        sentence mycroft should speak
                expect_response (bool): set to True if Mycroft should listen
                                        for a response immediately after
                                        speaking the utterance.
                wait (bool):            set to True to block while the text
                                        is being spoken.
        """
        # registers the skill as being active
        self.enclosure.register(self.name)
        data = {'utterance': utterance,
                'expect_response': expect_response}
        message = dig_for_message()
        if message:
            self.bus.emit(message.reply("speak", data))
        else:
            self.bus.emit(Message("speak", data))
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
        data = data or {}
        self.speak(self.dialog_renderer.render(key, data),
                   expect_response, wait)

    def init_dialog(self, root_directory):
        # If "<skill>/dialog/<lang>" exists, load from there.  Otherwise
        # load dialog from "<skill>/locale/<lang>"
        dialog_dir = join(root_directory, 'dialog', self.lang)
        if exists(dialog_dir):
            self.dialog_renderer = DialogLoader().load(dialog_dir)
        elif exists(join(root_directory, 'locale', self.lang)):
            locale_path = join(root_directory, 'locale', self.lang)
            self.dialog_renderer = DialogLoader().load(locale_path)
        else:
            LOG.debug('No dialog loaded')

    def load_data_files(self, root_directory):
        self.root_dir = root_directory
        self.init_dialog(root_directory)
        self.load_vocab_files(root_directory)
        self.load_regex_files(root_directory)

    def load_vocab_files(self, root_directory):
        vocab_dir = join(root_directory, 'vocab', self.lang)
        if exists(vocab_dir):
            load_vocabulary(vocab_dir, self.bus, self.skill_id)
        elif exists(join(root_directory, 'locale', self.lang)):
            load_vocabulary(join(root_directory, 'locale', self.lang),
                            self.bus, self.skill_id)
        else:
            LOG.debug('No vocab loaded')

    def load_regex_files(self, root_directory):
        regex_dir = join(root_directory, 'regex', self.lang)
        if exists(regex_dir):
            load_regex(regex_dir, self.bus, self.skill_id)
        elif exists(join(root_directory, 'locale', self.lang)):
            load_regex(join(root_directory, 'locale', self.lang),
                       self.bus, self.skill_id)

    def __handle_stop(self, event):
        """
            Handler for the "mycroft.stop" signal. Runs the user defined
            `stop()` method.
        """

        def __stop_timeout():
            # The self.stop() call took more than 100ms, assume it handled Stop
            self.bus.emit(Message("mycroft.stop.handled",
                                  {"skill_id": str(self.skill_id) + ":"}))

        timer = Timer(0.1, __stop_timeout)  # set timer for 100ms
        try:
            if self.stop():
                self.bus.emit(Message("mycroft.stop.handled",
                                      {"by": "skill:"+str(self.skill_id)}))
            timer.cancel()
        except Exception:
            timer.cancel()
            LOG.error("Failed to stop skill: {}".format(self.name),
                      exc_info=True)

    @abc.abstractmethod
    def stop(self):
        pass

    def shutdown(self):
        """
        This method is intended to be called during the skill
        process termination. The skill implementation must
        shutdown all processes and operations in execution.
        """
        pass

    def default_shutdown(self):
        """Parent function called internally to shut down everything.

        Shuts down known entities and calls skill specific shutdown method.
        """
        try:
            self.shutdown()
        except Exception as e:
            LOG.error('Skill specific shutdown function encountered '
                      'an error: {}'.format(repr(e)))
        # Store settings
        if exists(self._dir):
            self.settings.store()
            self.settings.stop_polling()
        # removing events
        self.cancel_all_repeating_events()
        for e, f in self.events:
            self.bus.remove(e, f)
        self.events = []  # Remove reference to wrappers

        self.bus.emit(
            Message("detach_skill", {"skill_id": str(self.skill_id) + ":"}))
        try:
            self.stop()
        except Exception:
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
            Takes scheduling information and sends it off on the message bus.
        """
        if not name:
            name = self.name + handler.__name__
        unique_name = self._unique_name(name)
        if repeat:
            self.scheduled_repeats.append(name)  # store "friendly name"

        data = data or {}
        self.add_event(unique_name, handler, once=not repeat)
        event_data = {}
        event_data['time'] = time.mktime(when.timetuple())
        event_data['event'] = unique_name
        event_data['repeat'] = repeat
        event_data['data'] = data
        self.bus.emit(Message('mycroft.scheduler.schedule_event',
                              data=event_data))

    def schedule_event(self, handler, when, data=None, name=None):
        """
            Schedule a single-shot event.

            Args:
                handler:               method to be called
                when (datetime/int):   datetime (in system timezone) or number
                                       of seconds in the future when the
                                       handler should be called
                data (dict, optional): data to send when the handler is called
                name (str, optional):  reference name
                                       NOTE: This will not warn or replace a
                                       previously scheduled event of the same
                                       name.
        """
        data = data or {}
        if isinstance(when, int):
            when = datetime.now() + timedelta(seconds=when)
        self._schedule_event(handler, when, data, name)

    def schedule_repeating_event(self, handler, when, frequency,
                                 data=None, name=None):
        """
            Schedule a repeating event.

            Args:
                handler:                method to be called
                when (datetime):        time (in system timezone) for first
                                        calling the handler, or None to
                                        initially trigger <frequency> seconds
                                        from now
                frequency (float/int):  time in seconds between calls
                data (dict, optional):  data to send when the handler is called
                name (str, optional):   reference name, must be unique
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
                name (str): reference name of event (from original scheduling)
        """
        data = data or {}
        data = {
            'event': self._unique_name(name),
            'data': data
        }
        self.bus.emit(Message('mycroft.schedule.update_event', data=data))

    def cancel_scheduled_event(self, name):
        """
            Cancel a pending event. The event will no longer be scheduled
            to be executed

            Args:
                name (str): reference name of event (from original scheduling)
        """
        unique_name = self._unique_name(name)
        data = {'event': unique_name}
        if name in self.scheduled_repeats:
            self.scheduled_repeats.remove(name)
        if self.remove_event(unique_name):
            self.bus.emit(Message('mycroft.scheduler.remove_event',
                                  data=data))

    def get_scheduled_event_status(self, name):
        """
            Get scheduled event data and return the amount of time left

            Args:
                name (str): reference name of event (from original scheduling)

            Return:
                int: the time left in seconds

            Raises:
                Exception: Raised if event is not found
        """
        event_name = self._unique_name(name)
        data = {'name': event_name}

        # making event_status an object so it's refrence can be changed
        event_status = None
        finished_callback = False

        def callback(message):
            nonlocal event_status
            nonlocal finished_callback
            if message.data is not None:
                event_time = int(message.data[0][0])
                current_time = int(time.time())
                time_left_in_seconds = event_time - current_time
                event_status = time_left_in_seconds
            finished_callback = True

        emitter_name = 'mycroft.event_status.callback.{}'.format(event_name)
        self.bus.once(emitter_name, callback)
        self.bus.emit(Message('mycroft.scheduler.get_event', data=data))

        start_wait = time.time()
        while finished_callback is False and time.time() - start_wait < 3.0:
            time.sleep(0.1)
        if time.time() - start_wait > 3.0:
            raise Exception("Event Status Messagebus Timeout")
        return event_status

    def cancel_all_repeating_events(self):
        """ Cancel any repeating events started by the skill. """
        # NOTE: Gotta make a copy of the list due to the removes that happen
        #       in cancel_scheduled_event().
        for e in list(self.scheduled_repeats):
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

    def __init__(self, name=None, bus=None):
        MycroftSkill.__init__(self, name, bus)

        #  list of fallback handlers registered by this instance
        self.instance_fallback_handlers = []

    @classmethod
    def make_intent_failure_handler(cls, bus):
        """Goes through all fallback handlers until one returns True"""

        def handler(message):
            # indicate fallback handling start
            bus.emit(message.reply("mycroft.skill.handler.start",
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
                            bus.emit(message.reply(
                                     'mycroft.skill.handler.complete',
                                     data={'handler': "fallback",
                                           "fallback_handler": handler_name}))
                            break
                    except Exception:
                        LOG.exception('Exception in fallback.')
                else:  # No fallback could handle the utterance
                    bus.emit(message.reply('complete_intent_failure'))
                    warning = "No fallback could handle intent."
                    LOG.warning(warning)
                    #  indicate completion with exception
                    bus.emit(message.reply('mycroft.skill.handler.complete',
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
        self._register_fallback(wrapper, priority)

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

    def default_shutdown(self):
        """
            Remove all registered handlers and perform skill shutdown.
        """
        self.remove_instance_handlers()
        super(FallbackSkill, self).default_shutdown()
