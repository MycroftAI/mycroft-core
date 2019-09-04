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
import inspect
import sys
import re
import traceback
from itertools import chain
from os import walk
from os.path import join, abspath, dirname, basename, exists
from threading import Event, Timer

from adapt.intent import Intent, IntentBuilder

from mycroft import dialog
from mycroft.api import DeviceApi
from mycroft.audio import wait_while_speaking
from mycroft.enclosure.api import EnclosureAPI
from mycroft.enclosure.gui import SkillGUI
from mycroft.configuration import Configuration
from mycroft.dialog import DialogLoader
from mycroft.filesystem import FileSystemAccess
from mycroft.messagebus.message import Message
from mycroft.metrics import report_metric
from mycroft.util import (
    resolve_resource_file,
    play_audio_file,
    camel_case_split
)
from mycroft.util.log import LOG

from .event_container import EventContainer, create_wrapper, get_handler_name
from ..event_scheduler import EventSchedulerInterface
from ..intent_service_interface import IntentServiceInterface
from ..settings import save_settings, Settings
from ..skill_data import (
    load_vocabulary,
    load_regex,
    to_alnum,
    munge_regex,
    munge_intent_parser,
    read_vocab_file,
    read_value_file,
    read_translated_file
)


def simple_trace(stack_trace):
    """Generate a simplified traceback.

    Arguments:
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

    Arguments:
        obj:    object to scan

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


def dig_for_message():
    """Dig Through the stack for message."""
    stack = inspect.stack()
    # Limit search to 10 frames back
    stack = stack if len(stack) < 10 else stack[:10]
    local_vars = [frame[0].f_locals for frame in stack]
    for l in local_vars:
        if 'message' in l and isinstance(l['message'], Message):
            return l['message']


class MycroftSkill:
    """Base class for mycroft skills providing common behaviour and parameters
    to all Skill implementations.

    For information on how to get started with creating mycroft skills see
    https://https://mycroft.ai/documentation/skills/introduction-developing-skills/

    Arguments:
        name (str): skill name
        bus (MycroftWebsocketClient): Optional bus connection
        use_settings (bool): Set to false to not use skill settings at all
    """
    def __init__(self, name=None, bus=None, use_settings=True):
        self.name = name or self.__class__.__name__
        self.resting_name = None
        self.skill_id = ''  # will be set from the path, so guaranteed unique
        self.skill_gid = None  # set when skill is loaded in SkillLoader
        # Get directory of skill
        self.root_dir = dirname(abspath(sys.modules[self.__module__].__file__))
        if use_settings:
            self.settings = Settings(self)
        else:
            self.settings = None
        self.settings_change_callback = None

        self.gui = SkillGUI(self)

        self._bus = None
        self._enclosure = None
        self.bind(bus)
        #: Mycroft global configuration. (dict)
        self.config_core = Configuration.get()
        self.dialog_renderer = None

        #: Filesystem access to skill specific folder.
        #: See mycroft.filesystem for details.
        self.file_system = FileSystemAccess(join('skills', self.name))

        self.log = LOG.create_logger(self.name)  #: Skill logger instance
        self.reload_skill = True  #: allow reloading (default True)

        self.events = EventContainer(bus)
        self.voc_match_cache = {}

        # Delegator classes
        self.event_scheduler = EventSchedulerInterface(self.name)
        self.intent_service = IntentServiceInterface()

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
        """Get the configured language."""
        return self.config_core.get('lang')

    def bind(self, bus):
        """Register messagebus emitter with skill.

        Arguments:
            bus: Mycroft messagebus connection
        """
        if bus:
            self._bus = bus
            self.events.set_bus(bus)
            self.intent_service.set_bus(bus)
            self.event_scheduler.set_bus(bus)
            self.event_scheduler.set_id(self.skill_id)
            self._enclosure = EnclosureAPI(bus, self.name)
            self._register_system_event_handlers()
            # Initialize the SkillGui
            self.gui.setup_default_handlers()

    def _register_system_event_handlers(self):
        """Add all events allowing the standard interaction with the Mycroft
        system.
        """
        self.add_event('mycroft.stop', self.__handle_stop)
        self.add_event(
            'mycroft.skill.enable_intent',
            self.handle_enable_intent
        )
        self.add_event(
            'mycroft.skill.disable_intent',
            self.handle_disable_intent
        )
        self.add_event(
            'mycroft.skill.set_cross_context',
            self.handle_set_cross_context
        )
        self.add_event(
            'mycroft.skill.remove_cross_context',
            self.handle_remove_cross_context
        )
        self.events.add(
            'mycroft.skills.settings.changed',
            self.handle_settings_change
        )

    def handle_settings_change(self, message):
        """Update settings if the remote settings changes apply to this skill.

        The skill settings downloader uses a single API call to retrieve the
        settings for all skills.  This is done to limit the number API calls.
        A "mycroft.skills.settings.changed" event is emitted for each skill
        that had their settings changed.  Only update this skill's settings
        if its remote settings were among those changed
        """
        if self.skill_gid is None:
            LOG.error('The skill_gid was not set when this skill was loaded!')
        else:
            remote_settings = message.data.get(self.skill_gid)
            if remote_settings is not None:
                self.settings.update(**remote_settings)
                if self.settings_change_callback is not None:
                    self.settings_change_callback()

    def detach(self):
        for (name, _) in self.intent_service:
            name = '{}:{}'.format(self.skill_id, name)
            self.intent_service.detach_intent(name)

    def initialize(self):
        """Perform any final setup needed for the skill.

        Invoked after the skill is fully constructed and registered with the
        system.
        """
        pass

    def get_intro_message(self):
        """Get a message to speak on first load of the skill.

        Useful for post-install setup instructions.

        Returns:
            str: message that will be spoken to the user
        """
        return None

    def converse(self, utterances, lang=None):
        """Handle conversation.

        This method gets a peek at utterances before the normal intent
        handling process after a skill has been invoked once.

        To use, override the converse() method and return True to
        indicate that the utterance has been handled.

        Arguments:
            utterances (list): The utterances from the user.  If there are
                               multiple utterances, consider them all to be
                               transcription possibilities.  Commonly, the
                               first entry is the user utt and the second
                               is normalized() version of the first utterance
            lang:       language the utterance is in, None for default

        Returns:
            bool: True if an utterance was handled, otherwise False
        """
        return False

    def __get_response(self):
        """Helper to get a reponse from the user

        Returns:
            str: user's response or None on a timeout
        """
        event = Event()

        def converse(utterances, lang=None):
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
        """Prompt user and wait for response

        The given dialog is spoken, followed immediately by listening
        for a user response.  The response can optionally be
        validated before returning.

        Example:
            color = self.get_response('ask.favorite.color')

        Arguments:
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

        if not self.dialog_renderer.render(dialog, data):
            raise ValueError('dialog message required')

        def on_fail_default(utterance):
            fail_data = data.copy()
            fail_data['utterance'] = utterance
            if on_fail:
                return self.dialog_renderer.render(on_fail, fail_data)
            else:
                return self.dialog_renderer.render(dialog, data)

        def is_cancel(utterance):
            return self.voc_match(utterance, 'cancel')

        def validator_default(utterance):
            # accept anything except 'cancel'
            return not is_cancel(utterance)

        on_fail_fn = on_fail if callable(on_fail) else on_fail_default
        validator = validator or validator_default

        # Speak query and wait for user response
        self.speak(self.dialog_renderer.render(dialog, data),
                   expect_response=True, wait=True)
        return self._wait_response(is_cancel, validator, on_fail_fn,
                                   num_retries)

    def _wait_response(self, is_cancel, validator, on_fail, num_retries):
        """Loop until a valid response is received from the user or the retry
        limit is reached.

        Arguments:
            is_cancel (callable): function checking cancel criteria
            validator (callbale): function checking for a valid response
            on_fail (callable): function handling retries

        """
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
            self.speak(line, expect_response=True)

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

    def voc_match(self, utt, voc_filename, lang=None):
        """Determine if the given utterance contains the vocabulary provided.

        Checks for vocabulary match in the utterance instead of the other
        way around to allow the user to say things like "yes, please" and
        still match against "Yes.voc" containing only "yes". The method first
        checks in the current skill's .voc files and secondly the "res/text"
        folder of mycroft-core. The result is cached to avoid hitting the
        disk each time the method is called.

        Arguments:
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
            if not voc:  # Check for vocab in mycroft core resources
                voc = resolve_resource_file(join('text', lang,
                                                 voc_filename + '.voc'))

            if not voc or not exists(voc):
                raise FileNotFoundError(
                        'Could not find {}.voc file'.format(voc_filename))
            # load vocab and flatten into a simple list
            vocab = read_vocab_file(voc)
            self.voc_match_cache[cache_key] = list(chain(*vocab))
        if utt:
            # Check for matches against complete words
            return any([re.match(r'.*\b' + i + r'\b.*', utt)
                        for i in self.voc_match_cache[cache_key]])
        else:
            return False

    def report_metric(self, name, data):
        """Report a skill metric to the Mycroft servers.

        Arguments:
            name (str): Name of metric. Must use only letters and hyphens
            data (dict): JSON dictionary to report. Must be valid JSON
        """
        report_metric('{}:{}'.format(basename(self.root_dir), name), data)

    def send_email(self, title, body):
        """Send an email to the registered user's email.

        Arguments:
            title (str): Title of email
            body  (str): HTML body of email. This supports
                         simple HTML like bold and italics
        """
        DeviceApi().send_email(title, body, basename(self.root_dir))

    def make_active(self):
        """Bump skill to active_skill list in intent_service.

        This enables converse method to be called even without skill being
        used in last 5 minutes.
        """
        self.bus.emit(Message('active_skill_request',
                              {'skill_id': self.skill_id}))

    def _handle_collect_resting(self, _=None):
        """Handler for collect resting screen messages.

        Sends info on how to trigger this skills resting page.
        """
        self.log.info('Registering resting screen')
        message = Message(
            'mycroft.mark2.register_idle',
            data={'name': self.resting_name, 'id': self.skill_id}
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

        Arguments:
            text (str): The base filename  (no extension needed)
            data (dict, optional): a JSON dictionary

        Returns:
            str: A randomly chosen string from the file
        """
        return self.dialog_renderer.render(text, data or {})

    def find_resource(self, res_name, res_dirname=None):
        """Find a resource file

        Searches for the given filename using this scheme:
        1) Search the resource lang directory:
             <skill>/<res_dirname>/<lang>/<res_name>
        2) Search the resource directory:
             <skill>/<res_dirname>/<res_name>
        3) Search the locale lang directory or other subdirectory:
             <skill>/locale/<lang>/<res_name> or
             <skill>/locale/<lang>/.../<res_name>

        Arguments:
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

        Arguments:
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

        Arguments:
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

        Arguments:
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

        Arguments:
            name (string): IntentParser name
            handler (func): Method to call
            handler_info (string): Base message when reporting skill event
                                   handler status on messagebus.
            once (bool, optional): Event handler will be removed after it has
                                   been run once.
        """
        skill_data = {'name': get_handler_name(handler)}

        def on_error(e):
            """Speak and log the error."""
            # Convert "MyFancySkill" to "My Fancy Skill" for speaking
            handler_name = camel_case_split(self.name)
            msg_data = {'skill': handler_name}
            msg = dialog.get('skill.error', self.lang, msg_data)
            self.speak(msg)
            LOG.exception(msg)
            # append exception information in message
            skill_data['exception'] = repr(e)

        def on_start(message):
            """Indicate that the skill handler is starting."""
            if handler_info:
                # Indicate that the skill handler is starting if requested
                msg_type = handler_info + '.start'
                self.bus.emit(message.reply(msg_type, skill_data))

        def on_end(message):
            """Store settings and indicate that the skill handler has completed
            """
            save_settings(self.root_dir, self.settings)
            if handler_info:
                msg_type = handler_info + '.complete'
                self.bus.emit(message.reply(msg_type, skill_data))

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

        Arguments:
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

        Arguments:
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

        Arguments:
            intent_file: name of file that contains example queries
                         that should activate the intent.  Must end with
                         '.intent'
            handler:     function to register with intent
        """
        name = '{}:{}'.format(self.skill_id, intent_file)
        filename = self.find_resource(intent_file, 'vocab')
        if not filename:
            raise FileNotFoundError('Unable to find "{}"'.format(intent_file))
        self.intent_service.register_padatious_intent(name, filename)
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
        filename = self.find_resource(entity_file + ".entity", 'vocab')
        if not filename:
            raise FileNotFoundError('Unable to find "{}"'.format(entity_file))

        name = '{}:{}'.format(self.skill_id, entity_file)
        self.intent_service.register_padatious_entity(name, filename)

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

        Arguments:
            intent_name (string): name of the intent to be disabled

        Returns:
                bool: True if disabled, False if it wasn't registered
        """
        if intent_name in self.intent_service:
            LOG.debug('Disabling intent ' + intent_name)
            name = '{}:{}'.format(self.skill_id, intent_name)
            self.intent_service.detach_intent(name)
            return True
        else:
            LOG.error('Could not disable '
                      '{}, it hasn\'t been registered.'.format(intent_name))
            return False

    def enable_intent(self, intent_name):
        """(Re)Enable a registered intent if it belongs to this skill.

        Arguments:
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
            LOG.debug('Enabling intent {}'.format(intent_name))
            return True
        else:
            LOG.error('Could not enable '
                      '{}, it hasn\'t been registered.'.format(intent_name))
            return False

    def set_context(self, context, word='', origin=''):
        """Add context to intent service

        Arguments:
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

        Arguments:
            context:    Keyword
            word:       word connected to keyword
        """
        self.bus.emit(Message('mycroft.skill.set_cross_context',
                              {'context': context, 'word': word,
                               'origin': self.skill_id}))

    def remove_cross_skill_context(self, context):
        """Tell all skills to remove a keyword from the context manager."""
        if not isinstance(context, str):
            raise ValueError('context should be a string')
        self.bus.emit(Message('mycroft.skill.remove_cross_context',
                              {'context': context}))

    def remove_context(self, context):
        """Remove a keyword from the context manager."""
        if not isinstance(context, str):
            raise ValueError('context should be a string')
        context = to_alnum(self.skill_id) + context
        self.intent_service.remove_adapt_context(context)

    def register_vocabulary(self, entity, entity_type):
        """ Register a word to a keyword

        Arguments:
            entity:         word to register
            entity_type:    Intent handler entity to tie the word to
        """
        self.bus.emit(Message('register_vocab', {
            'start': entity, 'end': to_alnum(self.skill_id) + entity_type
        }))

    def register_regex(self, regex_str):
        """Register a new regex.
        Arguments:
            regex_str: Regex string
        """
        regex = munge_regex(regex_str, self.skill_id)
        re.compile(regex)  # validate regex
        self.intent_service.register_adapt_regex(regex)

    def speak(self, utterance, expect_response=False, wait=False):
        """Speak a sentence.

        Arguments:
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
        m = message.reply("speak", data) if message else Message("speak", data)
        self.bus.emit(m)

        if wait:
            wait_while_speaking()

    def speak_dialog(self, key, data=None, expect_response=False, wait=False):
        """ Speak a random sentence from a dialog file.

        Arguments:
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

    def load_data_files(self, root_directory=None):
        """Load data files (intents, dialogs, etc).

        Arguments:
            root_directory (str): root folder to use when loading files.
        """
        root_directory = root_directory or self.root_dir
        self.init_dialog(root_directory)
        self.load_vocab_files(root_directory)
        self.load_regex_files(root_directory)

    def load_vocab_files(self, root_directory):
        """ Load vocab files found under root_directory.

        Arguments:
            root_directory (str): root folder to use when loading files
        """
        keywords = []
        vocab_dir = join(root_directory, 'vocab', self.lang)
        locale_dir = join(root_directory, 'locale', self.lang)
        if exists(vocab_dir):
            keywords = load_vocabulary(vocab_dir, self.skill_id)
        elif exists(locale_dir):
            keywords = load_vocabulary(locale_dir, self.skill_id)
        else:
            LOG.debug('No vocab loaded')

        # For each found intent register the default along with any aliases
        for vocab_type in keywords:
            for line in keywords[vocab_type]:
                entity = line[0]
                aliases = line[1:]
                self.intent_service.register_adapt_keyword(vocab_type,
                                                           entity,
                                                           aliases)

    def load_regex_files(self, root_directory):
        """ Load regex files found under the skill directory.

        Arguments:
            root_directory (str): root folder to use when loading files
        """
        regexes = []
        regex_dir = join(root_directory, 'regex', self.lang)
        locale_dir = join(root_directory, 'locale', self.lang)
        if exists(regex_dir):
            regexes = load_regex(regex_dir, self.skill_id)
        elif exists(locale_dir):
            regexes = load_regex(locale_dir, self.skill_id)

        for regex in regexes:
            self.intent_service.register_adapt_regex(regex)

    def __handle_stop(self, _):
        """Handler for the "mycroft.stop" signal. Runs the user defined
        `stop()` method.
        """

        def __stop_timeout():
            # The self.stop() call took more than 100ms, assume it handled Stop
            self.bus.emit(Message('mycroft.stop.handled',
                                  {'skill_id': str(self.skill_id) + ':'}))

        timer = Timer(0.1, __stop_timeout)  # set timer for 100ms
        try:
            if self.stop():
                self.bus.emit(Message("mycroft.stop.handled",
                                      {"by": "skill:" + self.skill_id}))
            timer.cancel()
        except Exception:
            timer.cancel()
            LOG.error('Failed to stop skill: {}'.format(self.name),
                      exc_info=True)

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
        try:
            self.shutdown()
        except Exception as e:
            LOG.error('Skill specific shutdown function encountered '
                      'an error: {}'.format(repr(e)))
        # Store settings
        if exists(self.root_dir):
            save_settings(self.root_dir, self.settings)

        # Clear skill from gui
        self.gui.clear()

        # removing events
        self.event_scheduler.shutdown()
        self.events.clear()

        self.bus.emit(
            Message('detach_skill', {'skill_id': str(self.skill_id) + ':'}))
        try:
            self.stop()
        except Exception:
            LOG.error('Failed to stop skill: {}'.format(self.name),
                      exc_info=True)

    def schedule_event(self, handler, when, data=None, name=None):
        """Schedule a single-shot event.

        Arguments:
            handler:               method to be called
            when (datetime/int/float):   datetime (in system timezone) or
                                   number of seconds in the future when the
                                   handler should be called
            data (dict, optional): data to send when the handler is called
            name (str, optional):  reference name
                                   NOTE: This will not warn or replace a
                                   previously scheduled event of the same
                                   name.
        """
        return self.event_scheduler.schedule_event(handler, when, data, name)

    def schedule_repeating_event(self, handler, when, frequency,
                                 data=None, name=None):
        """Schedule a repeating event.

        Arguments:
            handler:                method to be called
            when (datetime):        time (in system timezone) for first
                                    calling the handler, or None to
                                    initially trigger <frequency> seconds
                                    from now
            frequency (float/int):  time in seconds between calls
            data (dict, optional):  data to send when the handler is called
            name (str, optional):   reference name, must be unique
        """
        return self.event_scheduler.schedule_repeating_event(
            handler,
            when,
            frequency,
            data,
            name
        )

    def update_scheduled_event(self, name, data=None):
        """Change data of event.

        Arguments:
            name (str): reference name of event (from original scheduling)
            data (dict): event data
        """
        return self.event_scheduler.update_scheduled_event(name, data)

    def cancel_scheduled_event(self, name):
        """Cancel a pending event. The event will no longer be scheduled
        to be executed

        Arguments:
            name (str): reference name of event (from original scheduling)
        """
        return self.event_scheduler.cancel_scheduled_event(name)

    def get_scheduled_event_status(self, name):
        """Get scheduled event data and return the amount of time left

        Arguments:
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
