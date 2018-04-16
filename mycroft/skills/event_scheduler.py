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
import json
import time
from threading import Thread

from os.path import isfile

from mycroft.messagebus.message import Message
from mycroft.util.log import LOG
import sys
if sys.version_info[0] < 3:
    from Queue import Queue
else:
    from queue import Queue


def repeat_time(sched_time, repeat):
    """Next scheduled time for repeating event. Asserts that the
    time is not in the past.

    Args:
        sched_time (float): Scheduled unix time for the event
        repeat (float):     Repeat period in seconds

    Returns: (float) time for next event
    """
    next_time = sched_time + repeat
    if next_time < time.time():
        # Schedule at an offset to assure no doubles
        next_time = time.time() + repeat
    return next_time


class EventScheduler(Thread):
    def __init__(self, emitter, schedule_file='/opt/mycroft/schedule.json'):
        """
            Create an event scheduler thread. Will send messages at a
            predetermined time to the registered targets.

            Args:
                emitter:        event emitter to use to send messages
                schedule_file:  File to store pending events to on shutdown
        """
        super(EventScheduler, self).__init__()
        self.events = {}
        self.emitter = emitter
        self.isRunning = True
        self.schedule_file = schedule_file
        if self.schedule_file:
            self.load()

        self.add = Queue()
        self.remove = Queue()
        self.update = Queue()
        self.emitter.on('mycroft.scheduler.schedule_event',
                        self.schedule_event_handler)
        self.emitter.on('mycroft.scheduler.remove_event',
                        self.remove_event_handler)
        self.emitter.on('mycroft.scheduler.update_event',
                        self.update_event_handler)
        self.emitter.on('mycroft.scheduler.get_event',
                        self.get_event_handler)
        self.start()

    def load(self):
        """
            Load json data with active events from json file.
        """
        if isfile(self.schedule_file):
            json_data = {}
            with open(self.schedule_file) as f:
                try:
                    json_data = json.load(f)
                except Exception as e:
                    LOG.error(e.message)
            current_time = time.time()
            for key in json_data:
                event_list = json_data[key]
                # discard non repeating events that has already happened
                self.events[key] = [tuple(e) for e in event_list
                                    if e[0] > current_time or e[1]]

    def fetch_new_events(self):
        """
            Fetch new events and add to list of pending events.
        """
        while not self.add.empty():
            event, sched_time, repeat, data = self.add.get(timeout=1)
            # get current list of scheduled times for event, [] if missing
            event_list = self.events.get(event, [])

            # Don't schedule if the event is repeating and already scheduled
            if repeat and event in self.events:
                LOG.debug('Repeating event {} is already scheduled, discarding'
                          .format(event))
            else:
                # add received event and time
                event_list.append((sched_time, repeat, data))
                self.events[event] = event_list

    def remove_events(self):
        """
            Remove event from event list.
        """
        while not self.remove.empty():
            event = self.remove.get()
            if event in self.events:
                self.events.pop(event)

    def update_events(self):
        """
            Update event list with new data.
        """
        while not self.remove.empty():
            event, data = self.update.get()
            # if there is an active event with this name
            if len(self.events.get(event, [])) > 0:
                time, repeat, _ = self.events[event][0]
                self.events[event][0] = (time, repeat, data)

    def run(self):
        while self.isRunning:
            self.check_state()
            time.sleep(0.5)

    def check_state(self):
        """
            Check if an event should be triggered.
        """
        # Remove events
        self.remove_events()
        # Fetch newly scheduled events
        self.fetch_new_events()
        # Update events
        self.update_events()

        # Check all events
        for event in self.events:
            current_time = time.time()
            e = self.events[event]
            # Get scheduled times that has passed
            passed = [(t, r, d) for (t, r, d) in e if t <= current_time]
            # and remaining times that we're still waiting for
            remaining = [(t, r, d) for t, r, d in e if t > current_time]
            # Trigger registered methods
            for sched_time, repeat, data in passed:
                self.emitter.emit(Message(event, data))
                # if this is a repeated event add a new trigger time
                if repeat:
                    next_time = repeat_time(sched_time, repeat)
                    remaining.append((next_time, repeat, data))
            # update list of events
            self.events[event] = remaining

    def schedule_event(self, event, sched_time, repeat=None, data=None):
        """ Send event to thread using thread safe queue. """
        data = data or {}
        self.add.put((event, sched_time, repeat, data))

    def schedule_event_handler(self, message):
        """
            Messagebus interface to the schedule_event method.
            Required data in the message envelope is
                event: event to emit
                time:  time to emit the event

            optional data is
                repeat: repeat interval
                data:   data to send along with the event

        """
        event = message.data.get('event')
        sched_time = message.data.get('time')
        repeat = message.data.get('repeat')
        data = message.data.get('data')
        if event and sched_time:
            self.schedule_event(event, sched_time, repeat, data)
        elif not event:
            LOG.error('Scheduled event name not provided')
        else:
            LOG.error('Scheduled event time not provided')

    def remove_event(self, event):
        """ Remove event using thread safe queue. """
        self.remove.put(event)

    def remove_event_handler(self, message):
        """ Messagebus interface to the remove_event method. """
        event = message.data.get('event')
        self.remove_event(event)

    def update_event(self, event, data):
        self.update((event, data))

    def update_event_handler(self, message):
        """ Messagebus interface to the update_event method. """
        event = message.data.get('event')
        data = message.data.get('data')
        self.update_event(event, data)

    def get_event_handler(self, message):
        """
            Messagebus interface to get_event.
            Emits another event sending event status
        """
        event_name = message.data.get("name")
        event = None
        if event_name in self.events:
            event = self.events[event_name]
        emitter_name = 'mycroft.event_status.callback.{}'.format(event_name)
        self.emitter.emit(Message(emitter_name, data=event))

    def store(self):
        """
            Write current schedule to disk.
        """
        with open(self.schedule_file, 'w') as f:
            json.dump(self.events, f)

    def clear_repeating(self):
        """
            Remove repeating events from events dict.
        """
        for e in self.events:
            self.events[e] = [i for i in self.events[e] if i[1] is None]

    def clear_empty(self):
        """
            Remove empty event entries from events dict
        """
        self.events = {k: self.events[k] for k in self.events
                       if self.events[k] != []}

    def shutdown(self):
        """ Stop the running thread. """
        self.isRunning = False
        # Remove listeners
        self.emitter.remove_all_listeners('mycroft.scheduler.schedule_event')
        self.emitter.remove_all_listeners('mycroft.scheduler.remove_event')
        self.emitter.remove_all_listeners('mycroft.scheduler.update_event')
        # Wait for thread to finish
        self.join()
        # Prune event list in preparation for saving
        self.clear_repeating()
        self.clear_empty()
        # Store all pending scheduled events
        self.store()
