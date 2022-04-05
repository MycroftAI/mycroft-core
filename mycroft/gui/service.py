from mycroft.messagebus import Message
from mycroft.messagebus.client import MessageBusClient
from mycroft.util import create_daemon, start_message_bus_client
from mycroft.configuration import Configuration, LocalConf, USER_CONFIG
from mycroft.util.log import LOG
from .namespace import NamespaceManager
from mycroft.gui.extensions import ExtensionsManager
from mycroft.util.process_utils import ProcessStatus, StatusCallbackMap, ProcessState

def on_started():
    LOG.info('Gui Service is starting up.')


def on_alive():
    LOG.info('Gui Service is alive.')


def on_ready():
    LOG.info('Gui Service is ready.')


def on_error(e='Unknown'):
    LOG.info(f'Gui Service failed to launch ({e})')


def on_stopping():
    LOG.info('Gui Service is shutting down...')


class GUIService:
    def __init__(self, alive_hook=on_alive, started_hook=on_started, ready_hook=on_ready,
                error_hook=on_error, stopping_hook=on_stopping):
        self.bus = MessageBusClient()
        self.gui = NamespaceManager(self.bus)
        callbacks = StatusCallbackMap(on_started=started_hook,
                                      on_alive=alive_hook,
                                      on_ready=ready_hook,
                                      on_error=error_hook,
                                      on_stopping=stopping_hook)
        self.status = ProcessStatus('gui_service', callback_map=callbacks)
        self.status.bind(self.bus)

    def run(self):
        """Start the GUI after it has been constructed."""
        # Allow exceptions to be raised to the GUI Service
        # if they may cause the Service to fail.
        self.status.set_alive()
        start_message_bus_client("GUI_SERVICE", self.bus)
        extension_manager = ExtensionsManager(
            "EXTENSION_SERVICE", self.bus, self.gui)
        self.status.set_ready()

    def is_alive(self):
        """Respond to is_alive status request."""
        return self.status.state >= ProcessState.ALIVE

    def stop(self):
        """Perform any GUI shutdown processes."""
        self.status.set_stopping()
