import json
import logging
import signal as sig
from threading import Event
from mycroft.util.log import LOG
from ovos_utils import create_daemon, wait_for_exit_signal

# backwards compat imports, DO NOT DELETE, careful with autopep8
from ovos_utils.process_utils import ProcessState, ProcessStatus, StatusCallbackMap


def reset_sigint_handler():
    """Reset the sigint handler to the default.

    This fixes KeyboardInterrupt not getting raised when started via
    start-mycroft.sh
    """
    sig.signal(sig.SIGINT, sig.default_int_handler)


_log_all_bus_messages = False


def bus_logging_status():
    global _log_all_bus_messages
    return _log_all_bus_messages


def _update_log_level(msg, name):
    """Update log level for process.

    Args:
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

    Args:
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


def start_message_bus_client(service, bus=None, whitelist=None):
    """Start the bus client daemon and wait for connection.

    Args:
        service (str): name of the service starting the connection
        bus (MessageBusClient): an instance of the Mycroft MessageBusClient
        whitelist (list, optional): List of "type" strings. If defined, only
                                    messages in this list will be logged.
    Returns:
        A connected instance of the MessageBusClient
    """
    # Local imports to avoid circular importing
    from mycroft.messagebus.client import MessageBusClient
    from mycroft.configuration import Configuration
    # Create a client if one was not provided
    if bus is None:
        bus = MessageBusClient()
    Configuration.set_config_update_handlers(bus)
    bus_connected = Event()
    bus.on('message', create_echo_function(service, whitelist))
    # Set the bus connected event when connection is established
    bus.once('open', bus_connected.set)
    create_daemon(bus.run_forever)

    # Wait for connection
    bus_connected.wait()
    LOG.info('Connected to messagebus')

    return bus
