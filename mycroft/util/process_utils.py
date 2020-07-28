from collections import namedtuple
from enum import IntEnum
import json
import logging
import signal as sig
import sys
from threading import Thread
from time import sleep

from .log import LOG


def reset_sigint_handler():
    """Reset the sigint handler to the default.

    This fixes KeyboardInterrupt not getting raised when started via
    start-mycroft.sh
    """
    sig.signal(sig.SIGINT, sig.default_int_handler)


def create_daemon(target, args=(), kwargs=None):
    """Helper to quickly create and start a thread with daemon = True"""
    t = Thread(target=target, args=args, kwargs=kwargs)
    t.daemon = True
    t.start()
    return t


def wait_for_exit_signal():
    """Blocks until KeyboardInterrupt is received."""
    try:
        while True:
            sleep(100)
    except KeyboardInterrupt:
        pass


_log_all_bus_messages = False


def bus_logging_status():
    global _log_all_bus_messages
    return _log_all_bus_messages


def _update_log_level(msg, name):
    """Update log level for process.

    Arguments:
        msg (Message): Message sent to trigger the log level change
        name (str): Name of the current process
    """
    global _log_all_bus_messages

    # Respond to requests to adjust the logger settings
    lvl = msg["data"].get("level", "").upper()
    if lvl in ["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"]:
        LOG.level = lvl
        LOG(name).info("Changing log level to: {}".format(lvl))
        try:
            logging.getLogger().setLevel(lvl)
            logging.getLogger('urllib3').setLevel(lvl)
        except Exception:
            pass  # We don't really care about if this fails...
    else:
        LOG(name).info("Invalid level provided: {}".format(lvl))

    # Allow enable/disable of messagebus traffic
    log_bus = msg["data"].get("bus", None)
    if log_bus is not None:
        LOG(name).info("Bus logging: {}".format(log_bus))
        _log_all_bus_messages = log_bus


def create_echo_function(name, whitelist=None):
    """Standard logging mechanism for Mycroft processes.

    This handles the setup of the basic logging for all Mycroft
    messagebus-based processes.
    TODO 20.08: extract log level setting thing completely from this function

    Arguments:
        name (str): Reference name of the process
        whitelist (list, optional): List of "type" strings. If defined, only
                                    messages in this list will be logged.

    Returns:
        func: The echo function
    """

    from mycroft.configuration import Configuration
    blacklist = Configuration.get().get("ignore_logs")

    # Make sure whitelisting doesn't remove the log level setting command
    if whitelist:
        whitelist.append('mycroft.debug.log')

    def echo(message):
        global _log_all_bus_messages
        try:
            msg = json.loads(message)
            msg_type = msg.get("type", "")
            # Whitelist match beginning of message
            # i.e 'mycroft.audio.service' will allow the message
            # 'mycroft.audio.service.play' for example
            if whitelist and not any([msg_type.startswith(e)
                                     for e in whitelist]):
                return

            if blacklist and msg_type in blacklist:
                return

            if msg_type == "mycroft.debug.log":
                _update_log_level(msg, name)
            elif msg_type == "registration":
                # do not log tokens from registration messages
                msg["data"]["token"] = None
                message = json.dumps(msg)
        except Exception as e:
            LOG.info("Error: {}".format(repr(e)), exc_info=True)

        if _log_all_bus_messages:
            # Listen for messages and echo them for logging
            LOG(name).info("BUS: {}".format(message))
    return echo


class ProcessState(IntEnum):

    """Oredered enum to make state checks easy.

    For example Alive can be determined using >= ProcessState.ALIVE,
    which will return True if the state is READY as well as ALIVE.
    """
    NOT_STARTED = 0
    STARTED = 1
    ERROR = 2
    STOPPING = 3
    ALIVE = 4
    READY = 5


# Process state change callback mappings.
_STATUS_CALLBACKS = [
    'on_started',
    'on_alive',
    'on_complete',
    'on_error',
    'on_stopping',
]
# namedtuple defaults only available on 3.7 and later python versions
if sys.version_info < (3, 7):
    StatusCallbackMap = namedtuple('CallbackMap', _STATUS_CALLBACKS)
    StatusCallbackMap.__new__.__defaults__ = (None,) * 5
else:
    StatusCallbackMap = namedtuple(
        'CallbackMap',
        _STATUS_CALLBACKS,
        defaults=(None,) * len(_STATUS_CALLBACKS),
    )


class ProcessStatus:
    """Process status tracker.

    The class tracks process status and execute callback methods on
    state changes as well as replies to messagebus queries of the
    process status.

    Arguments:
        name (str): process name, will be used to create the messagebus
                    messagetype "mycroft.{name}...".
        bus (MessageBusClient): Connection to the Mycroft messagebus.
        callback_map (StatusCallbackMap): optionally, status callbacks for the
                                          various status changes.
    """

    def __init__(self, name, bus, callback_map=None):

        # Messagebus connection
        self.bus = bus
        self.name = name

        self.callbacks = callback_map or StatusCallbackMap()
        self.state = ProcessState.NOT_STARTED
        self._register_handlers()

    def _register_handlers(self):
        """Register messagebus handlers for status queries."""
        self.bus.on('mycroft.{}.is_alive'.format(self.name), self.check_alive)
        self.bus.on('mycroft.{}.ready'.format(self.name), self.check_ready)
        # The next one is for backwards compatibility
        # TODO: remove in 21.02
        self.bus.on(
            'mycroft.{}.all_loaded'.format(self.name), self.check_ready
        )

    def check_alive(self, message=None):
        """Respond to is_alive status request.

        Arguments:
            message: Optional message to respond to, if omitted no message
                     is sent.

        Returns:
            bool, True if process is alive.
        """
        is_alive = self.state >= ProcessState.ALIVE

        if message:
            status = {'status': is_alive}
            self.bus.emit(message.response(data=status))

        return is_alive

    def check_ready(self, message=None):
        """Respond to all_loaded status request.

        Arguments:
            message: Optional message to respond to, if omitted no message
                     is sent.

        Returns:
            bool, True if process is ready.
        """
        is_ready = self.state >= ProcessState.READY
        if message:
            status = {'status': is_ready}
            self.bus.emit(message.response(data=status))

        return is_ready

    def set_started(self):
        """Process is started."""
        self.state = ProcessState.STARTED
        if self.callbacks.on_started:
            self.callbacks.on_started()

    def set_alive(self):
        """Basic loading is done."""
        self.state = ProcessState.ALIVE
        if self.callbacks.on_alive:
            self.callbacks.on_alive()

    def set_ready(self):
        """All loading is done."""
        self.state = ProcessState.READY
        if self.callbacks.on_complete:
            self.callbacks.on_complete()

    def set_stopping(self):
        """Process shutdown has started."""
        self.state = ProcessState.STOPPING
        if self.callbacks.on_stopping:
            self.callbacks.on_stopping()

    def set_error(self, err=''):
        """An error has occured and the process is non-functional."""
        # Intentionally leave is_started True
        self.state = ProcessState.ERROR
        if self.callbacks.on_error:
            self.callbacks.on_error(err)
