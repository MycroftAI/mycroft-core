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
from pyee import EventEmitter
from multiprocessing.pool import ThreadPool
from collections import defaultdict


class ThreadedEventEmitter(EventEmitter):
    """ Event Emitter using the threadpool to run event functions in
        separate threads.
    """
    def __init__(self, threads=10):
        super().__init__()
        self.pool = ThreadPool(threads)
        self.wrappers = defaultdict(list)

    def on(self, event, f=None):
        """ Wrap on with a threaded launcher. """
        def wrapped(*args, **kwargs):
            return self.pool.apply_async(f, args, kwargs)

        w = super().on(event, wrapped)
        # Store mapping from function to wrapped function
        self.wrappers[event].append((f, wrapped))
        return w

    def once(self, event, f=None):
        """ Wrap once with a threaded launcher. """
        def wrapped(*args, **kwargs):
            return self.pool.apply_async(f, args, kwargs)

        wrapped = super().once(event, wrapped)
        self.wrappers[event].append((f, wrapped))
        return wrapped

    def remove_listener(self, event_name, func):
        """ Wrap the remove to translate from function to wrapped
            function.
        """
        for w in self.wrappers[event_name]:
            if w[0] == func:
                self.wrappers[event_name].remove(w)
                return super().remove_listener(event_name, w[1])
        # if no wrapper exists try removing the function
        return super().remove_listener(event_name, func)

    def remove_all_listeners(self, event_name):
        """Remove all listeners with name.

        event_name: identifier of event handler
        """
        super().remove_all_listeners(event_name)
        self.wrappers.pop(event_name)
