from mycroft.messagebus.message import Message
from mycroft.util.log import getLogger

from threading import Thread
from Queue import Queue
import time
import json
from os.path import isfile


logger = getLogger(__name__)


class EventScheduler(Thread):
    def __init__(self, emitter, schedule_file='/opt/mycroft/schedule.json'):
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
        self.start()

    def load(self):
        """
            Load json data with active events from json file.
        """
        if isfile(self.schedule_file):
            with open(self.schedule_file) as f:
                try:
                    json_data = json.load(f)
                except Exception as e:
                    logger.error(e)
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
            # Fetch newly scheduled events
            self.fetch_new_events()
            # Remove events
            self.remove_events()
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
                        remaining.append((sched_time + repeat, repeat, data))
                # update list of events
                self.events[event] = remaining
            time.sleep(0.5)

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
            logger.error('Scheduled event name not provided')
        else:
            logger.error('Scheduled event time not provided')

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

    def store(self):
        """
            Write current schedule to disk.
        """
        with open(self.schedule_file, 'w') as f:
            json.dump(self.events, f)

    def shutdown(self):
        """ Stop the running thread. """
        self.isRunning = False
        # Remove listeners
        self.emitter.remove_all_listeners('mycroft.scheduler.schedule_event')
        self.emitter.remove_all_listeners('mycroft.scheduler.remove_event')
        self.emitter.remove_all_listeners('mycroft.scheduler.update_event')
        # Wait for thread to finish
        self.join()
        # Store all pending scheduled events
        self.store()
