from mycroft.messagebus import Message
from mycroft.messagebus.client import MessageBusClient
from mycroft.util import create_daemon, start_message_bus_client
from mycroft.configuration import Configuration, LocalConf, USER_CONFIG
from mycroft.util.log import LOG
from .namespace import NamespaceManager
from mycroft.gui.extensions import ExtensionsManager


class GUIService:
    def __init__(self):
        self.bus = MessageBusClient()
        self.gui = NamespaceManager(self.bus)

    def run(self):
        """Start the GUI after it has been constructed."""
        # Allow exceptions to be raised to the GUI Service
        # if they may cause the Service to fail.
        start_message_bus_client("GUI_SERVICE", self.bus)
        extension_manager = ExtensionsManager(
            "EXTENSION_SERVICE", self.bus, self.gui)

    def stop(self):
        """Perform any GUI shutdown processes."""
        pass
