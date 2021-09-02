# Copyright 2017 Mycroft AI, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import inspect
import json
import os

import padaos
import sys
from functools import wraps
from subprocess import call, check_output
from threading import Thread

from padatious.match_data import MatchData
from padatious.entity import Entity
from padatious.entity_manager import EntityManager
from padatious.intent_manager import IntentManager
from padatious.util import tokenize


def _save_args(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        func(*args, **kwargs)
        bound_args = inspect.signature(func).bind(*args, **kwargs)
        bound_args.apply_defaults()
        kwargs = bound_args.arguments
        kwargs['__name__'] = func.__name__
        kwargs.pop('self').serialized_args.append(kwargs)

    return wrapper


class IntentContainer(object):
    """
    Creates an IntentContainer object used to load and match intents

    Args:
        cache_dir (str): Place to put all saved neural networks
    """

    def __init__(self, cache_dir):
        os.makedirs(cache_dir, exist_ok=True)
        self.cache_dir = cache_dir
        self.must_train = False
        self.intents = IntentManager(cache_dir)
        self.entities = EntityManager(cache_dir)
        self.padaos = padaos.IntentContainer()
        self.train_thread = None  # type: Thread
        self.serialized_args = []  # Arguments of all calls to register intents/entities

    def clear(self):
        os.makedirs(self.cache_dir, exist_ok=True)
        self.must_train = False
        self.intents = IntentManager(self.cache_dir)
        self.entities = EntityManager(self.cache_dir)
        self.padaos = padaos.IntentContainer()
        self.train_thread = None
        self.serialized_args = []

    def instantiate_from_disk(self):
        """
                Instantiates the necessary (internal) data structures when loading persisted model from disk.
                This is done via injecting entities and intents back from cached file versions.
                """

        # ToDo: still padaos.compile (regex compilation) is redone when loading
        for f in os.listdir(self.cache_dir):
            if f.startswith('{') and f.endswith('}.hash'):
                entity_name = f[1:f.find('}.hash')]
                self.add_entity(
                    name=entity_name,
                    lines=[],
                    reload_cache=False,
                    must_train=False)
            elif not f.startswith('{') and f.endswith('.hash'):
                intent_name = f[0:f.find('.hash')]
                self.add_intent(
                    name=intent_name,
                    lines=[],
                    reload_cache=False,
                    must_train=False)

    @_save_args
    def add_intent(self, name, lines, reload_cache=False, must_train=True):
        """
        Creates a new intent, optionally checking the cache first

        Args:
            name (str): The associated name of the intent
            lines (list<str>): All the sentences that should activate the intent
            reload_cache: Whether to ignore cached intent if exists
        """
        self.intents.add(name, lines, reload_cache, must_train)
        self.padaos.add_intent(name, lines)
        self.must_train = must_train

    @_save_args
    def add_entity(self, name, lines, reload_cache=False, must_train=True):
        """
        Adds an entity that matches the given lines.

        Example:
            self.add_intent('weather', ['will it rain on {weekday}?'])
            self.add_entity('weekday', ['monday', 'tuesday', 'wednesday'])  # ...

        Args:
            name (str): The name of the entity
            lines (list<str>): Lines of example extracted entities
            reload_cache (bool): Whether to refresh all of cache
                must_train (bool): Whether to dismiss model if present and train from scratch again
        """
        Entity.verify_name(name)
        self.entities.add(
            Entity.wrap_name(name),
            lines,
            reload_cache,
            must_train)
        self.padaos.add_entity(name, lines)
        self.must_train = must_train

    @_save_args
    def load_entity(
            self,
            name,
            file_name,
            reload_cache=False,
            must_train=True):
        """
       Loads an entity, optionally checking the cache first

       Args:
           name (str): The associated name of the entity
           file_name (str): The location of the entity file
           reload_cache (bool): Whether to refresh all of cache
           must_train (bool): Whether to dismiss model if present and train from scratch again
       """
        Entity.verify_name(name)
        self.entities.load(Entity.wrap_name(name), file_name, reload_cache)
        with open(file_name, encoding='utf8') as f:
            self.padaos.add_entity(name, f.read().split('\n'))
        self.must_train = must_train

    @_save_args
    def load_file(self, *args, **kwargs):
        """Legacy. Use load_intent instead"""
        self.load_intent(*args, **kwargs)

    @_save_args
    def load_intent(
            self,
            name,
            file_name,
            reload_cache=False,
            must_train=True):
        """
        Loads an intent, optionally checking the cache first

        Args:
            name (str): The associated name of the intent
            file_name (str): The location of the intent file
            reload_cache (bool): Whether to refresh all of cache
            must_train (bool): Whether to dismiss model if present and train from scratch again
        """
        self.intents.load(name, file_name, reload_cache)
        with open(file_name, encoding='utf8') as f:
            self.padaos.add_intent(name, f.read().split('\n'))
        self.must_train = must_train

    @_save_args
    def remove_intent(self, name):
        """Unload an intent"""
        self.intents.remove(name)
        self.padaos.remove_intent(name)
        self.must_train = True

    @_save_args
    def remove_entity(self, name):
        """Unload an entity"""
        self.entities.remove(name)
        self.padaos.remove_entity(name)

    def _train(self, *args, **kwargs):
        t1 = Thread(
            target=self.intents.train,
            args=args,
            kwargs=kwargs,
            daemon=True)
        t2 = Thread(
            target=self.entities.train,
            args=args,
            kwargs=kwargs,
            daemon=True)
        t1.start()
        t2.start()
        t1.join()
        t2.join()
        self.entities.calc_ent_dict()

    def train(self, debug=True, force=False, single_thread=False, timeout=20):
        """
        Trains all the loaded intents that need to be updated
        If a cache file exists with the same hash as the intent file,
        the intent will not be trained and just loaded from file

        Args:
            debug (bool): Whether to print a message to stdout each time a new intent is trained
            force (bool): Whether to force training if already finished
            single_thread (bool): Whether to force running in a single thread
            timeout (float): Seconds before cancelling training
        Returns:
            bool: True if training succeeded without timeout
        """
        if not self.must_train and not force:
            return
        self.padaos.compile()
        self.train_thread = Thread(target=self._train, kwargs=dict(
            debug=debug,
            single_thread=single_thread,
            timeout=timeout
        ), daemon=True)
        self.train_thread.start()
        self.train_thread.join(timeout)

        self.must_train = False
        return not self.train_thread.is_alive()

    def train_subprocess(self, *args, **kwargs):
        """
        Trains in a subprocess which provides a timeout guarantees everything shuts down properly

        Args:
            See <train>
        Returns:
            bool: True for success, False if timed out
        """
        ret = call([
            sys.executable, '-m', 'padatious', 'train', self.cache_dir,
            '-d', json.dumps(self.serialized_args),
            '-a', json.dumps(args),
            '-k', json.dumps(kwargs),
        ])
        if ret == 2:
            raise TypeError(
                'Invalid train arguments: {} {}'.format(
                    args, kwargs))
        data = self.serialized_args
        self.clear()
        self.apply_training_args(data)
        self.padaos.compile()
        if ret == 0:
            self.must_train = False
            return True
        elif ret == 10:  # timeout
            return False
        else:
            raise ValueError(
                'Training failed and returned code: {}'.format(ret))

    def calc_intents(self, query):
        """
        Tests all the intents against the query and returns
        data on how well each one matched against the query

        Args:
            query (str): Input sentence to test against intents
        Returns:
            list<MatchData>: List of intent matches
        See calc_intent() for a description of the returned MatchData
        """
        if self.must_train:
            self.train()
        intents = {} if self.train_thread and self.train_thread.is_alive() else {
            i.name: i for i in self.intents.calc_intents(query, self.entities)
        }
        sent = tokenize(query)
        for perfect_match in self.padaos.calc_intents(query):
            name = perfect_match['name']
            intents[name] = MatchData(
                name, sent, matches=perfect_match['entities'], conf=1.0)
        return list(intents.values())

    def calc_intent(self, query):
        """
        Tests all the intents against the query and returns
        match data of the best intent

        Args:
            query (str): Input sentence to test against intents
        Returns:
            MatchData: Best intent match
        """
        matches = self.calc_intents(query)
        if len(matches) == 0:
            return MatchData('', '')
        best_match = max(matches, key=lambda x: x.conf)
        best_matches = (
            match for match in matches if match.conf == best_match.conf)
        return min(best_matches, key=lambda x: sum(
            map(len, x.matches.values())))

    def get_training_args(self):
        return self.serialized_args

    def apply_training_args(self, data):
        for params in data:
            func_name = params.pop('__name__')
            getattr(self, func_name)(**params)
