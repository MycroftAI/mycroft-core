#!/usr/bin/env python3
import typing

from mycroft.messagebus import Message
from mycroft.util import LOG


class Activity:
    """Base class for activities"""

    def __init__(self, name: str, bus):
        self.name = name
        self.bus = bus
        self.log = LOG.create_logger(self.name)

        self._started_event = f"{self.name}.started"
        self._ended_event = f"{self.name}.ended"

        self.bus.on(self._started_event, self.handle_started)
        self.bus.on(self._ended_event, self.handle_ended)

    def started(self):
        """Called when activity has started"""
        pass

    def handle_started(self, _):
        """Runs started() in respose to started event"""
        self.started()

    def ended(self):
        """Called when activity has ended"""
        pass

    def handle_ended(self, _):
        """Runs ended() in response to ended event"""
        self.ended()

    def end(self):
        """Emits ended event"""
        self.bus.emit(Message(self._ended_event))

    def run(self):
        """Starts activity"""
        self.bus.emit(Message(self._started_event))
