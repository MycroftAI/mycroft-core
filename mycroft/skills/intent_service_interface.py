# Copyright 2018 Mycroft AI Inc.
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
"""The intent service interface offers a unified wrapper class for the
Intent Service. Including both adapt and padatious.
"""
from os.path import exists

from adapt.intent import Intent

from mycroft.messagebus.message import Message


class IntentServiceInterface:
    """Interface to communicate with the Mycroft intent service.

    This class wraps the messagebus interface of the intent service allowing
    for easier interaction with the service. It wraps both the Adapt and
    Precise parts of the intent services.
    """
    def __init__(self, bus=None):
        self.bus = bus
        self.registered_intents = []

    def set_bus(self, bus):
        self.bus = bus

    def register_adapt_keyword(self, vocab_type, entity, aliases=None):
        """Send a message to the intent service to add an Adapt keyword.

            vocab_type(str): Keyword reference
            entity (str): Primary keyword
            aliases (list): List of alternative kewords
        """
        aliases = aliases or []
        self.bus.emit(Message("register_vocab",
                              {'start': entity, 'end': vocab_type}))
        for alias in aliases:
            self.bus.emit(Message("register_vocab", {
                'start': alias, 'end': vocab_type, 'alias_of': entity
            }))

    def register_adapt_regex(self, regex):
        """Register a regex with the intent service.

        Arguments:
            regex (str): Regex to be registered, (Adapt extracts keyword
                         reference from named match group.
        """
        self.bus.emit(Message("register_vocab", {'regex': regex}))

    def register_adapt_intent(self, name, intent_parser):
        """Register an Adapt intent parser object.

        Serializes the intent_parser and sends it over the messagebus to
        registered.
        """
        self.bus.emit(Message("register_intent", intent_parser.__dict__))
        self.registered_intents.append((name, intent_parser))

    def detach_intent(self, intent_name):
        """Remove an intent from the intent service.

        Arguments:
            intent_name(str): Intent reference
        """
        self.bus.emit(Message("detach_intent", {"intent_name": intent_name}))

    def set_adapt_context(self, context, word, origin):
        """Set an Adapt context.

        Arguments:
            context (str): context keyword name
            word (str): word to register
            origin (str): original origin of the context (for cross context)
        """
        self.bus.emit(Message('add_context',
                              {'context': context, 'word': word,
                               'origin': origin}))

    def remove_adapt_context(self, context):
        """Remove an active Adapt context.

        Arguments:
            context(str): name of context to remove
        """
        self.bus.emit(Message('remove_context', {'context': context}))

    def register_padatious_intent(self, intent_name, filename):
        """Register a padatious intent file with Padatious.

        Arguments:
            intent_name(str): intent identifier
            filename(str): complete file path for entity file
        """
        if not isinstance(filename, str):
            raise ValueError('Filename path must be a string')
        if not exists(filename):
            raise FileNotFoundError('Unable to find "{}"'.format(filename))

        data = {"file_name": filename,
                "name": intent_name}
        self.bus.emit(Message("padatious:register_intent", data))
        self.registered_intents.append((intent_name.split(':')[-1], data))

    def register_padatious_entity(self, entity_name, filename):
        """Register a padatious entity file with Padatious.

        Arguments:
            entity_name(str): entity name
            filename(str): complete file path for entity file
        """
        if not isinstance(filename, str):
            raise ValueError('Filename path must be a string')
        if not exists(filename):
            raise FileNotFoundError('Unable to find "{}"'.format(filename))

        self.bus.emit(Message('padatious:register_entity', {
            'file_name': filename,
            'name': entity_name
        }))

    def __iter__(self):
        """Iterator over the registered intents.

        Returns an iterator returning name-handler pairs of the registered
        intent handlers.
        """
        return iter(self.registered_intents)

    def __contains__(self, val):
        """Checks if an intent name has been registered."""
        return val in [i[0] for i in self.registered_intents]

    def get_intent(self, intent_name):
        """Get intent from intent_name.

        Arguments:
            intent_name (str): name to find.

        Returns:
            Found intent or None if none were found.
        """
        for name, intent in self:
            if name == intent_name:
                return intent
        else:
            return None


def open_intent_envelope(message):
    """Convert dictionary received over messagebus to Intent."""
    intent_dict = message.data
    return Intent(intent_dict.get('name'),
                  intent_dict.get('requires'),
                  intent_dict.get('at_least_one'),
                  intent_dict.get('optional'))
