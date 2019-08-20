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
from os.path import exists

from adapt.intent import Intent

from mycroft.messagebus.message import Message
from mycroft.util.log import LOG


class IntentServiceInterface:
    def __init__(self, bus=None):
        self.bus = bus
        self.registered_intents = []

    def set_bus(self, bus):
        self.bus = bus

    def register_adapt_keyword(self, vocab_type, entity, aliases=None):
        aliases = aliases or []
        self.bus.emit(Message("register_vocab",
                              {'start': entity, 'end': vocab_type}))
        for alias in aliases:
            self.bus.emit(Message("register_vocab", {
                'start': alias, 'end': vocab_type, 'alias_of': entity
            }))

    def register_adapt_regex(self, regex):
        self.bus.emit(Message("register_vocab", {'regex': regex}))

    def register_adapt_intent(self, name, intent_parser):
        self.bus.emit(Message("register_intent", intent_parser.__dict__))
        self.registered_intents.append((name, intent_parser))

    def detach_intent(self, name):
        self.bus.emit(Message("detach_intent", {"intent_name": name}))

    def set_adapt_context(self, context, word, origin):
        self.bus.emit(Message('add_context',
                              {'context': context, 'word': word,
                               'origin': origin}))

    def remove_adapt_context(self, context):
        self.bus.emit(Message('remove_context', {'context': context}))

    def register_padatious_intent(self, name, filename):
        if not filename:
            raise FileNotFoundError('Unable to find "{}"'.format(filename))

        data = {"file_name": filename,
                "name": name}
        self.bus.emit(Message("padatious:register_intent", data))
        self.registered_intents.append((name, data))

    def register_padatious_entity(self, name, filename):
        if not filename or not exists(filename):
            raise FileNotFoundError('Unable to find "{}"'.format(filename))

        self.bus.emit(Message("padatious:register_entity", {
            "file_name": filename,
            "name": name
        }))

    def __iter__(self):
        return iter(self.registered_intents)

    def __contains__(self, val):
        return val in [i[0] for i in self.registered_intents]

    def get_intent(self, intent_name):
        names = [intent[0] for intent in self]
        intents = [intent[1] for intent in self]
        if intent_name in names:
            return intents[names.index(intent_name)]
        else:
            return None


def open_intent_envelope(message):
    """Convert dictionary received over messagebus to Intent."""
    intent_dict = message.data
    return Intent(intent_dict.get('name'),
                  intent_dict.get('requires'),
                  intent_dict.get('at_least_one'),
                  intent_dict.get('optional'))
