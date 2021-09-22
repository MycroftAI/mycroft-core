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
import multiprocessing as mp
from functools import partial
from multiprocessing.context import TimeoutError
from os.path import join, isfile, isdir, splitext

import padatious
from padatious.train_data import TrainData
from padatious.util import lines_hash


def _train_and_save(obj, cache, data, print_updates):
    """Internal pickleable function used to train objects in another process"""
    obj.train(data)
    if print_updates:
        print('Regenerated ' + obj.name + '.')
    obj.save(cache)


class TrainingManager(object):
    """
    Manages multithreaded training of either Intents or Entities

    Args:
        cls (Type[Trainable]): Class to wrap
        cache_dir (str): Place to store cache files
    """

    def __init__(self, cls, cache_dir):
        self.cls = cls
        self.cache = cache_dir
        self.objects = []
        self.objects_to_train = []

        self.train_data = TrainData()

    def add(self, name, lines, reload_cache=False, must_train=True):

        # special case: load persisted (aka. cached) resource (i.e.
        # entity or intent) from file into memory data structures
        if not must_train:
            self.objects.append(
                self.cls.from_file(
                    name=name,
                    folder=self.cache))
            # general case: load resource (entity or intent) to training queue
            # or if no change occurred to memory data structures
        else:
            hash_fn = join(self.cache, name + '.hash')
            old_hsh = None
            if isfile(hash_fn):
                with open(hash_fn, 'rb') as g:
                    old_hsh = g.read()
            min_ver = splitext(padatious.__version__)[0]
            new_hsh = lines_hash([min_ver] + lines)
            if reload_cache or old_hsh != new_hsh:
                self.objects_to_train.append(self.cls(name=name, hsh=new_hsh))
            else:
                self.objects.append(
                    self.cls.from_file(
                        name=name, folder=self.cache))
            self.train_data.add_lines(name, lines)

    def load(self, name, file_name, reload_cache=False):
        # mycroft-zh: fix charset issue.
        # with open(file_name) as f:
        with open(file_name, 'r', encoding='utf8') as f:
            self.add(name, f.read().split('\n'), reload_cache)

    def remove(self, name):
        self.objects = [i for i in self.objects if i.name != name]
        self.objects_to_train = [
            i for i in self.objects_to_train if i.name != name]
        self.train_data.remove_lines(name)

    def train(self, debug=True, single_thread=False, timeout=20):
        train = partial(
            _train_and_save,
            cache=self.cache,
            data=self.train_data,
            print_updates=debug)

        if single_thread:
            for i in self.objects_to_train:
                train(i)
        else:
            # Train in multiple processes to disk
            pool = mp.Pool()
            try:
                pool.map_async(train, self.objects_to_train).get(timeout)
            except TimeoutError:
                if debug:
                    print('Some objects timed out while training')
            finally:
                pool.close()
                pool.join()

        # Load saved objects from disk
        for obj in self.objects_to_train:
            try:
                self.objects.append(
                    self.cls.from_file(
                        name=obj.name,
                        folder=self.cache))
            except IOError:
                if debug:
                    print('Took too long to train', obj.name)
        self.objects_to_train = []
