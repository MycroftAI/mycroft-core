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
from os.path import exists, isfile
from adapt.intent import Intent

from mycroft.messagebus.message import Message, dig_for_message
from mycroft.messagebus.client import MessageBusClient
from mycroft.util import create_daemon
from mycroft.util.log import LOG


class IntentServiceInterface:
    """Interface to communicate with the Mycroft intent service.

    This class wraps the messagebus interface of the intent service allowing
    for easier interaction with the service. It wraps both the Adapt and
    Padatious parts of the intent services.
    """

    def __init__(self, bus=None):
        self.bus = bus
        self.skill_id = self.__class__.__name__
        self.registered_intents = []

    def set_bus(self, bus):
        self.bus = bus

    def set_id(self, skill_id):
        self.skill_id = skill_id

    def register_adapt_keyword(self, vocab_type, entity, aliases=None, lang=None):
        """Send a message to the intent service to add an Adapt keyword.

            vocab_type(str): Keyword reference
            entity (str): Primary keyword
            aliases (list): List of alternative keywords
        """
        msg = dig_for_message() or Message("")
        if "skill_id" not in msg.context:
            msg.context["skill_id"] = self.skill_id

        # TODO 22.02: Remove compatibility data
        aliases = aliases or []
        entity_data = {'entity_value': entity,
                       'entity_type': vocab_type,
                       'lang': lang}
        compatibility_data = {'start': entity, 'end': vocab_type}

        self.bus.emit(msg.forward("register_vocab",
                                  {**entity_data, **compatibility_data}))
        for alias in aliases:
            alias_data = {
                'entity_value': alias,
                'entity_type': vocab_type,
                'alias_of': entity,
                'lang': lang}
            compatibility_data = {'start': alias, 'end': vocab_type}
            self.bus.emit(msg.forward("register_vocab",
                                      {**alias_data, **compatibility_data}))

    def register_adapt_regex(self, regex, lang=None):
        """Register a regex with the intent service.

        Args:
            regex (str): Regex to be registered, (Adapt extracts keyword
                         reference from named match group.
        """
        msg = dig_for_message() or Message("")
        if "skill_id" not in msg.context:
            msg.context["skill_id"] = self.skill_id
        self.bus.emit(msg.forward("register_vocab",
                                  {'regex': regex, 'lang': lang}))

    def register_adapt_intent(self, name, intent_parser):
        """Register an Adapt intent parser object.

        Serializes the intent_parser and sends it over the messagebus to
        registered.
        """
        msg = dig_for_message() or Message("")
        if "skill_id" not in msg.context:
            msg.context["skill_id"] = self.skill_id
        self.bus.emit(msg.forward("register_intent", intent_parser.__dict__))
        self.registered_intents.append((name, intent_parser))

    def detach_intent(self, intent_name):
        """Remove an intent from the intent service.

        Args:
            intent_name(str): Intent reference
        """
        msg = dig_for_message() or Message("")
        if "skill_id" not in msg.context:
            msg.context["skill_id"] = self.skill_id
        self.bus.emit(msg.forward("detach_intent",
                                  {"intent_name": intent_name}))

    def set_adapt_context(self, context, word, origin):
        """Set an Adapt context.

        Args:
            context (str): context keyword name
            word (str): word to register
            origin (str): original origin of the context (for cross context)
        """
        msg = dig_for_message() or Message("")
        if "skill_id" not in msg.context:
            msg.context["skill_id"] = self.skill_id
        self.bus.emit(msg.forward('add_context',
                                  {'context': context, 'word': word,
                                   'origin': origin}))

    def remove_adapt_context(self, context):
        """Remove an active Adapt context.

        Args:
            context(str): name of context to remove
        """
        msg = dig_for_message() or Message("")
        if "skill_id" not in msg.context:
            msg.context["skill_id"] = self.skill_id
        self.bus.emit(msg.forward('remove_context', {'context': context}))

    def register_padatious_intent(self, intent_name, filename, lang):
        """Register a padatious intent file with Padatious.

        Args:
            intent_name(str): intent identifier
            filename(str): complete file path for entity file
        """
        if not isinstance(filename, str):
            raise ValueError('Filename path must be a string')
        if not exists(filename):
            raise FileNotFoundError('Unable to find "{}"'.format(filename))

        data = {'file_name': filename,
                'name': intent_name,
                'lang': lang}
        msg = dig_for_message() or Message("")
        if "skill_id" not in msg.context:
            msg.context["skill_id"] = self.skill_id
        self.bus.emit(msg.forward("padatious:register_intent", data))
        self.registered_intents.append((intent_name.split(':')[-1], data))

    def register_padatious_entity(self, entity_name, filename, lang):
        """Register a padatious entity file with Padatious.

        Args:
            entity_name(str): entity name
            filename(str): complete file path for entity file
        """
        if not isinstance(filename, str):
            raise ValueError('Filename path must be a string')
        if not exists(filename):
            raise FileNotFoundError('Unable to find "{}"'.format(filename))
        msg = dig_for_message() or Message("")
        if "skill_id" not in msg.context:
            msg.context["skill_id"] = self.skill_id
        self.bus.emit(msg.forward('padatious:register_entity',
                                  {'file_name': filename,
                                   'name': entity_name,
                                   'lang': lang}))

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

        Args:
            intent_name (str): name to find.

        Returns:
            Found intent or None if none were found.
        """
        for name, intent in self:
            if name == intent_name:
                return intent
        else:
            return None


class IntentQueryApi:
    """
    Query Intent Service at runtime
    """

    def __init__(self, bus=None, timeout=5):
        if bus is None:
            bus = MessageBusClient()
            create_daemon(bus.run_forever)
        self.bus = bus
        self.timeout = timeout

    def get_adapt_intent(self, utterance, lang="en-us"):
        """ get best adapt intent for utterance """
        msg = Message("intent.service.adapt.get",
                      {"utterance": utterance, "lang": lang},
                      context={"destination": "intent_service",
                               "source": "intent_api"})

        resp = self.bus.wait_for_response(msg,
                                          'intent.service.adapt.reply',
                                          timeout=self.timeout)
        data = resp.data if resp is not None else {}
        if not data:
            LOG.error("Intent Service timed out!")
            return None
        return data["intent"]

    def get_padatious_intent(self, utterance, lang="en-us"):
        """ get best padatious intent for utterance """
        msg = Message("intent.service.padatious.get",
                      {"utterance": utterance, "lang": lang},
                      context={"destination": "intent_service",
                               "source": "intent_api"})
        resp = self.bus.wait_for_response(msg,
                                          'intent.service.padatious.reply',
                                          timeout=self.timeout)
        data = resp.data if resp is not None else {}
        if not data:
            LOG.error("Intent Service timed out!")
            return None
        return data["intent"]

    def get_intent(self, utterance, lang="en-us"):
        """ get best intent for utterance """
        msg = Message("intent.service.intent.get",
                      {"utterance": utterance, "lang": lang},
                      context={"destination": "intent_service",
                               "source": "intent_api"})
        resp = self.bus.wait_for_response(msg,
                                          'intent.service.intent.reply',
                                          timeout=self.timeout)
        data = resp.data if resp is not None else {}
        if not data:
            LOG.error("Intent Service timed out!")
            return None
        return data["intent"]

    def get_skill(self, utterance, lang="en-us"):
        """ get skill that utterance will trigger """
        intent = self.get_intent(utterance, lang)
        if not intent:
            return None
        # theoretically skill_id might be missing
        if intent.get("skill_id"):
            return intent["skill_id"]
        # retrieve skill from munged intent name
        if intent.get("intent_name"):  # padatious + adapt
            return intent["name"].split(":")[0]
        if intent.get("intent_type"):  # adapt
            return intent["intent_type"].split(":")[0]
        return None  # raise some error here maybe? this should never happen

    def get_skills_manifest(self):
        msg = Message("intent.service.skills.get",
                      context={"destination": "intent_service",
                               "source": "intent_api"})
        resp = self.bus.wait_for_response(msg,
                                          'intent.service.skills.reply',
                                          timeout=self.timeout)
        data = resp.data if resp is not None else {}
        if not data:
            LOG.error("Intent Service timed out!")
            return None
        return data["skills"]

    def get_active_skills(self, include_timestamps=False):
        msg = Message("intent.service.active_skills.get",
                      context={"destination": "intent_service",
                               "source": "intent_api"})
        resp = self.bus.wait_for_response(msg,
                                          'intent.service.active_skills.reply',
                                          timeout=self.timeout)
        data = resp.data if resp is not None else {}
        if not data:
            LOG.error("Intent Service timed out!")
            return None
        if include_timestamps:
            return data["skills"]
        return [s[0] for s in data["skills"]]

    def get_adapt_manifest(self):
        msg = Message("intent.service.adapt.manifest.get",
                      context={"destination": "intent_service",
                               "source": "intent_api"})
        resp = self.bus.wait_for_response(msg,
                                          'intent.service.adapt.manifest',
                                          timeout=self.timeout)
        data = resp.data if resp is not None else {}
        if not data:
            LOG.error("Intent Service timed out!")
            return None
        return data["intents"]

    def get_padatious_manifest(self):
        msg = Message("intent.service.padatious.manifest.get",
                      context={"destination": "intent_service",
                               "source": "intent_api"})
        resp = self.bus.wait_for_response(msg,
                                          'intent.service.padatious.manifest',
                                          timeout=self.timeout)
        data = resp.data if resp is not None else {}
        if not data:
            LOG.error("Intent Service timed out!")
            return None
        return data["intents"]

    def get_intent_manifest(self):
        padatious = self.get_padatious_manifest()
        adapt = self.get_adapt_manifest()
        return {"adapt": adapt,
                "padatious": padatious}

    def get_vocab_manifest(self):
        msg = Message("intent.service.adapt.vocab.manifest.get",
                      context={"destination": "intent_service",
                               "source": "intent_api"})
        reply_msg_type = 'intent.service.adapt.vocab.manifest'
        resp = self.bus.wait_for_response(msg,
                                          reply_msg_type,
                                          timeout=self.timeout)
        data = resp.data if resp is not None else {}
        if not data:
            LOG.error("Intent Service timed out!")
            return None

        vocab = {}
        for voc in data["vocab"]:
            if voc.get("regex"):
                continue
            if voc["end"] not in vocab:
                vocab[voc["end"]] = {"samples": []}
            vocab[voc["end"]]["samples"].append(voc["start"])
        return [{"name": voc, "samples": vocab[voc]["samples"]}
                for voc in vocab]

    def get_regex_manifest(self):
        msg = Message("intent.service.adapt.vocab.manifest.get",
                      context={"destination": "intent_service",
                               "source": "intent_api"})
        reply_msg_type = 'intent.service.adapt.vocab.manifest'
        resp = self.bus.wait_for_response(msg,
                                          reply_msg_type,
                                          timeout=self.timeout)
        data = resp.data if resp is not None else {}
        if not data:
            LOG.error("Intent Service timed out!")
            return None

        vocab = {}
        for voc in data["vocab"]:
            if not voc.get("regex"):
                continue
            name = voc["regex"].split("(?P<")[-1].split(">")[0]
            if name not in vocab:
                vocab[name] = {"samples": []}
            vocab[name]["samples"].append(voc["regex"])
        return [{"name": voc, "regexes": vocab[voc]["samples"]}
                for voc in vocab]

    def get_entities_manifest(self):
        msg = Message("intent.service.padatious.entities.manifest.get",
                      context={"destination": "intent_service",
                               "source": "intent_api"})
        reply_msg_type = 'intent.service.padatious.entities.manifest'
        resp = self.bus.wait_for_response(msg,
                                          reply_msg_type,
                                          timeout=self.timeout)
        data = resp.data if resp is not None else {}
        if not data:
            LOG.error("Intent Service timed out!")
            return None

        entities = []
        # read files
        for ent in data["entities"]:
            if isfile(ent["file_name"]):
                with open(ent["file_name"]) as f:
                    lines = f.read().replace("(", "").replace(")", "").split(
                        "\n")
                samples = []
                for l in lines:
                    samples += [a.strip() for a in l.split("|") if a.strip()]
                entities.append({"name": ent["name"], "samples": samples})
        return entities

    def get_keywords_manifest(self):
        padatious = self.get_entities_manifest()
        adapt = self.get_vocab_manifest()
        regex = self.get_regex_manifest()
        return {"adapt": adapt,
                "padatious": padatious,
                "regex": regex}


def open_intent_envelope(message):
    """Convert dictionary received over messagebus to Intent."""
    intent_dict = message.data
    return Intent(intent_dict.get('name'),
                  intent_dict.get('requires'),
                  intent_dict.get('at_least_one'),
                  intent_dict.get('optional'))
