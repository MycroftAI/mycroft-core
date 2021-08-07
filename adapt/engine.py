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

import re
import heapq
import pyee
from adapt.entity_tagger import EntityTagger
from adapt.parser import Parser
from adapt.tools.text.tokenizer import EnglishTokenizer
from adapt.tools.text.trie import Trie

__author__ = 'seanfitz'


class IntentDeterminationEngine(pyee.EventEmitter):
    """
    IntentDeterminationEngine

    The IntentDeterminationEngine is a greedy and naive implementation of intent determination. Given an utterance,
    it uses the Adapt parsing tools to come up with a sorted collection of tagged parses. A valid parse result contains
    no overlapping tagged entities, and its confidence is the sum of the tagged entity confidences, which are
    weighted based on the percentage of the utterance (per character) that the entity match represents.

    This system makes heavy use of generators to enable greedy algorithms to short circuit large portions of
    computation.
    """
    def __init__(self, tokenizer=None, trie=None):
        """
        Initialize the IntentDeterminationEngine

        Args:
            tokenizer(tokenizer) : tokenizer used to break up spoken text
                example EnglishTokenizer()
            trie(Trie): tree of matches to Entites
        """
        pyee.EventEmitter.__init__(self)
        self.tokenizer = tokenizer or EnglishTokenizer()
        self.trie = trie or Trie()
        self.regular_expressions_entities = []
        self._regex_strings = set()
        self.tagger = EntityTagger(self.trie, self.tokenizer, self.regular_expressions_entities)
        self.intent_parsers = []

    def __best_intent(self, parse_result, context=[]):
        """
        Decide the best intent

        Args:
            parse_result(list): results used to match the best intent.
            context(list): ?

        Returns:
            best_intent, best_tags:
                best_intent : The best intent for given results
                best_tags : The Tags for result
        """
        best_intent = None
        best_tags = None
        # TODO: there's a bunch of subtlety here around what the values of `match` and `key` should be
        # Longer term, this should probably be typed, barring any performance regressions.
        context_as_entities = [
            {
                'key': c['key'],
                'entities': [c],
                'from_context': True
             } for c in context
        ]
        for intent in self.intent_parsers:
            i, tags = intent.validate_with_tags(parse_result.get('tags') + context_as_entities, parse_result.get('confidence'))
            if not best_intent or (i and i.get('confidence') > best_intent.get('confidence')):
                best_intent = i
                best_tags = tags

        return best_intent, best_tags

    def __get_unused_context(self, parse_result, context):
        """ Used to get unused context from context.  Any keys not in
        parse_result

        Args:
            parse_results(list): parsed results used to identify what keys
                in the context are used.
            context(list): this is the context used to match with parsed results
                keys missing in the parsed results are the unused context

        Returns:
            list: A list of the unused context results.
        """
        tags_keys = set([t['key'] for t in parse_result['tags'] if t['from_context']])
        result_context = [c for c in context if c['key'] not in tags_keys]
        return result_context

    def determine_intent(self, utterance, num_results=1, include_tags=False, context_manager=None):
        """
        Given an utterance, provide a valid intent.

        Args:
            utterance(str): an ascii or unicode string representing natural language speech
            include_tags(bool): includes the parsed tags (including position and confidence)
                as part of result
            context_manager(list): a context manager to provide context to the utterance
            num_results(int): a maximum number of results to be returned.

        Returns: A generator that yields dictionaries.
        """
        parser = Parser(self.tokenizer, self.tagger)
        parser.on('tagged_entities',
                  (lambda result:
                   self.emit("tagged_entities", result)))

        context = []
        if context_manager:
            context = context_manager.get_context()

        for result in parser.parse(utterance, N=num_results, context=context):
            self.emit("parse_result", result)
            # create a context without entities used in result
            remaining_context = self.__get_unused_context(result, context)
            best_intent, tags = self.__best_intent(result, remaining_context)
            if best_intent and best_intent.get('confidence', 0.0) > 0:
                if include_tags:
                    best_intent['__tags__'] = tags
                yield best_intent

    def register_entity(self, entity_value, entity_type, alias_of=None):
        """
        Register an entity to be tagged in potential parse results

        Args:
            entity_value(str): the value/proper name of an entity instance (Ex: "The Big Bang Theory")
            entity_type(str): the type/tag of an entity instance (Ex: "Television Show")
        """
        if alias_of:
            self.trie.insert(entity_value.lower(), data=(alias_of, entity_type))
        else:
            self.trie.insert(entity_value.lower(), data=(entity_value, entity_type))
            self.trie.insert(entity_type.lower(), data=(entity_type, 'Concept'))

    def register_regex_entity(self, regex_str):
        """
        A regular expression making use of python named group expressions.

        Example: (?P<Artist>.*)

        regex_str(str): a string representing a regular expression as defined above
        """
        if regex_str and regex_str not in self._regex_strings:
            self._regex_strings.add(regex_str)
            self.regular_expressions_entities.append(re.compile(regex_str, re.IGNORECASE))

    def register_intent_parser(self, intent_parser):
        """
        "Enforce" the intent parser interface at registration time.

        Args:
            intent_parser(intent): Intent to be registered.

        Raises:
            ValueError: on invalid intent
        """
        if hasattr(intent_parser, 'validate') and callable(intent_parser.validate):
            self.intent_parsers.append(intent_parser)
        else:
            raise ValueError("%s is not an intent parser" % str(intent_parser))

    def drop_intent_parser(self, parser_names):
        """Drop a registered intent parser.

        Arguments:
            parser_names (str or iterable): parser name to drop or list of
                                            names

        Returns:
            (bool) True if a parser was dropped else False
        """
        if isinstance(parser_names, str):
            parser_names = [parser_names]

        new_parsers = [p for p in self.intent_parsers
                       if p.name not in parser_names]
        num_original_parsers = len(self.intent_parsers)
        self.intent_parsers = new_parsers

        return len(self.intent_parsers) != num_original_parsers

    def drop_entity(self, entity_type=None, match_func=None):
        """Drop all entities mathching the given entity type or match function

        Arguments:
            entity_type (str): entity name to match against
            match_func (callable): match function to find entities

        Returns:
            (bool) True if vocab was found and removed otherwise False.
        """
        def default_match_func(data):
            return data and data[1] == entity_type

        ent_tuples = self.trie.scan(match_func or default_match_func)
        for entity in ent_tuples:
            self.trie.remove(*entity)

        return len(ent_tuples) != 0

    def drop_regex_entity(self, entity_type=None, match_func=None):
        """Remove registered regex entity.

        Arguments:
            entity_type (str): entity name to match against
            match_func (callable): match function to find entities

        Returns:
            (bool) True if vocab was found and removed otherwise False.
        """
        def default_match_func(regexp):
            return entity_type in regexp.groupindex.keys()

        match_func = match_func or default_match_func
        matches = [r for r in self.regular_expressions_entities
                   if match_func(r)]
        matching_patterns = [r.pattern for r in matches]

        self.regular_expressions_entities = [
            r for r in self.regular_expressions_entities if r not in matches
        ]
        self._regex_strings = [
            r for r in self._regex_strings if r not in matching_patterns
        ]

        return len(matches) != 0


class DomainIntentDeterminationEngine(object):
    """
    DomainIntentDeterminationEngine.

    The DomainIntentDeterminationEngine is a greedy and naive implementation of intent
    determination. Given an utterance, it uses the Adapt parsing tools to come up with a
    sorted collection of tagged parses. A valid parse result contains no overlapping
    tagged entities in a single domain, and its confidence is the sum of the tagged
    entity confidences, which are weighted based on the percentage of the utterance
    (per character) that the entity match represents.

    This system makes heavy use of generators to enable greedy algorithms to short circuit
    large portions of computation.
    """

    def __init__(self):
        """
        Initialize DomainIntentDeterminationEngine.

        Args:
            tokenizer(tokenizer): The tokenizer you wish to use.
            trie(Trie): the Trie() you wish to use.
            domain(str): a string representing the domain you wish to add
        """
        self.domains = {}

    @property
    def tokenizer(self):
        """
        A property to link into IntentEngine's tokenizer.

        Warning: this is only for backwards compatiblility and should not be used if you
            intend on using domains.

        Return: the domains tokenizer from its IntentEngine
        """
        domain = 0
        if domain not in self.domains:
            self.register_domain(domain=domain)
        return self.domains[domain].tokenizer

    @property
    def trie(self):
        """
        A property to link into IntentEngine's trie.

        warning:: this is only for backwards compatiblility and should not be used if you
        intend on using domains.

        Return: the domains trie from its IntentEngine
        """
        domain = 0
        if domain not in self.domains:
            self.register_domain(domain=domain)
        return self.domains[domain].trie

    @property
    def tagger(self):
        """
        A property to link into IntentEngine's intent_parsers.

        Warning: this is only for backwards compatiblility and should not be used if you
        intend on using domains.

        Return: the domains intent_parsers from its IntentEngine
        """
        domain = 0
        if domain not in self.domains:
            self.register_domain(domain=domain)
        return self.domains[domain].tagger

    @property
    def intent_parsers(self):
        """
        A property to link into IntentEngine's intent_parsers.

        Warning: this is only for backwards compatiblility and should not be used if you
            intend on using domains.

        Returns: the domains intent_parsers from its IntentEngine
        """
        domain = 0
        if domain not in self.domains:
            self.register_domain(domain=domain)
        return self.domains[domain].intent_parsers

    @property
    def _regex_strings(self):
        """
        A property to link into IntentEngine's _regex_strings.

        Warning: this is only for backwards compatiblility and should not be used if you
            intend on using domains.

        Returns: the domains _regex_strings from its IntentEngine
        """
        domain = 0
        if domain not in self.domains:
            self.register_domain(domain=domain)
        return self.domains[domain]._regex_strings

    @property
    def regular_expressions_entities(self):
        """
        A property to link into IntentEngine's regular_expressions_entities.

        Warning: this is only for backwards compatiblility and should not be used if you
            intend on using domains.

        Returns: the domains regular_expression_entities from its IntentEngine
        """
        domain = 0
        if domain not in self.domains:
            self.register_domain(domain=domain)
        return self.domains[domain].regular_expressions_entities

    def register_domain(self, domain=0, tokenizer=None, trie=None):
        """
        Register a domain with the intent engine.

        Args:
            tokenizer(tokenizer): The tokenizer you wish to use.
            trie(Trie): the Trie() you wish to use.
            domain(str): a string representing the domain you wish to add
        """
        self.domains[domain] = IntentDeterminationEngine(
            tokenizer=tokenizer, trie=trie)

    def register_entity(self, entity_value, entity_type, alias_of=None, domain=0):
        """
        Register an entity to be tagged in potential parse results.

        Args:
            entity_value(str): the value/proper name of an entity instance
                (Ex: "The Big Bang Theory")
            entity_type(str): the type/tag of an entity instance (Ex: "Television Show")
            domain(str): a string representing the domain you wish to add the entity to
        """
        if domain not in self.domains:
            self.register_domain(domain=domain)
        self.domains[domain].register_entity(entity_value=entity_value,
                                             entity_type=entity_type,
                                             alias_of=alias_of)

    def register_regex_entity(self, regex_str, domain=0):
        """
        A regular expression making use of python named group expressions.

        Example: (?P<Artist>.*)

        Args:
            regex_str(str): a string representing a regular expression as defined above
            domain(str): a string representing the domain you wish to add the entity to
        """
        if domain not in self.domains:
            self.register_domain(domain=domain)
        self.domains[domain].register_regex_entity(regex_str=regex_str)

    def determine_intent(self, utterance, num_results=1):
        """
        Given an utterance, provide a valid intent.

        utterance(str): an ascii or unicode string representing natural language speech
        num_results(int): a maximum number of results to be returned.

        Returns: A generator the yields dictionaries.
        """
        intents = []
        for domain in self.domains:
            gen = self.domains[domain].determine_intent(utterance=utterance,
                                                        num_results=1)
            for intent in gen:
                intents.append(intent)

        heapq.nlargest(
            num_results, intents, key=lambda domain: domain['confidence'])
        for intent in intents:
            yield intent

    def register_intent_parser(self, intent_parser, domain=0):
        """
        Register a intent parser with a domain.

        Args:
            intent_parser(intent): The intent parser you wish to register.
            domain(str): a string representing the domain you wish register the intent
                parser to.
        """
        if domain not in self.domains:
            self.register_domain(domain=domain)
        self.domains[domain].register_intent_parser(
            intent_parser=intent_parser)

    def drop_intent_parser(self, parser_names, domain):
        """Drop a registered intent parser.

        Arguments:
            parser_names (list, str): parser names to drop.
            domain (str): domain to drop from

        Returns:
            (bool) True if an intent parser was dropped else false.
        """
        return self.domains[domain].drop_intent_parser(parser_names)

    def drop_entity(self, domain, entity_type=None, match_func=None):
        """Drop all entities mathching the given entity type or match function.

        Arguments:
            domain (str): intent domain
            entity_type (str): entity name to match against
            match_func (callable): match function to find entities

        Returns:
            (bool) True if vocab was found and removed otherwise False.
        """
        return self.domains[domain].drop_entity(entity_type=entity_type,
                                                match_func=match_func)

    def drop_regex_entity(self, domain, entity_type=None, match_func=None):
        """Remove registered regex entity.

        Arguments:
            domain (str): intent domain
            entity_type (str): entity name to match against
            match_func (callable): match function to find entities

        Returns:
            (bool) True if vocab was found and removed otherwise False.
        """
        return self.domains[domain].drop_regex_entity(entity_type=entity_type,
                                                      match_func=match_func)
