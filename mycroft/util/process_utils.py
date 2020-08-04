import json
import logging
import signal as sig
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


class ProcessStatus:
    def __init__(self, name, bus,
                 on_started=None, on_alive=None, on_ready=None,
                 on_stopping=None, on_error=None):
        # Messagebus connection
        self.bus = bus
        self.name = name

        # Callback functions
        self.on_started = on_started
        self.on_alive = on_alive
        self.on_ready = on_ready
        self.on_error = on_error

        # State variables
        self.is_started = False
        self.is_alive = False
        self.is_ready = False

        self._register_handlers()

    def _register_handlers(self):
        self.bus.on('mycroft.{}.is_started'.format(self.name),
                    self.check_started)
        self.bus.on('mycroft.{}.is_alive'.format(self.name), self.check_alive)
        self.bus.on('mycroft.{}.is_ready'.format(self.name),
                    self.check_ready)
        self.bus.on('mycroft.{}.all_loaded'.format(self.name),
                    self.check_ready)

    def check_started(self, message=None):
        """Respond to is_started status request."""
        if message:
            status = {'status': self.is_started}
            self.bus.emit(message.response(data=status))
        return self.is_started

    def check_alive(self, message=None):
        """Respond to is_alive status request."""
        if message:
            status = {'status': self.is_alive}
            self.bus.emit(message.response(data=status))
        return self.is_alive

    def check_ready(self, message=None):
        """ Respond to all_loaded status request."""
        if message:
            status = {'status': self.is_ready}
            self.bus.emit(message.response(data=status))

        return self.is_ready

    def set_started(self):
        """Process is started."""
        self.is_started = True
        if self.on_started:
            self.on_started()

    def set_alive(self):
        """Basic loading is done."""
        self.is_alive = True
        self.is_started = True
        if self.on_alive:
            self.on_alive()

    def set_ready(self):
        """All loading is done."""
        self.is_alive = True
        self.is_ready = True
        if self.on_ready:
            self.on_ready()

    def set_stopping(self):
        self.is_ready = False
        if self.on_stopping:
            self.on_stopping()

    def set_error(self, err=''):
        self.is_ready = False
        self.is_alive = False
        if self.on_stopping:
            self.on_ready(err)
