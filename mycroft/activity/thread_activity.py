#!/usr/bin/env python3
import threading
import typing
import abc

from mycroft.messagebus import Message
from mycroft.util import LOG


class ThreadActivity(abc.ABC):
    """Base class for activities"""

    def __init__(self, name: str, bus):
        self.name = name
        self.bus = bus
        self.log = LOG.create_logger(self.name)

        self._started_event = f"{self.name}.started"
        self._ended_event = f"{self.name}.ended"
        self._error_event = f"{self.name}.error"

        self._thread: typing.Optional[threading.Thread] = None
        self._block_event = threading.Event()

    def started(self):
        """Called when activity has started"""
        pass

    def ended(self):
        """Called when activity has ended"""
        pass

    def run(self, block: bool = True, timeout: typing.Optional[float] = None):
        """Starts activity"""
        self._thread = threading.Thread(target=self._thread_proc, daemon=True)
        self._thread.start()

        if block:
            self._block_event.wait(timeout=timeout)

    def _thread_proc(self):
        """Runs activity inside thread"""
        try:
            self.bus.emit(Message(self._started_event))
            self.started()
            self.bus.emit(Message(self._ended_event))
            self.ended()
        except Exception as error:
            self.log.exception("error in activity %s", self.name)
            self.bus.emit(
                Message(self._error_event, data={"error": str(error)})
            )
