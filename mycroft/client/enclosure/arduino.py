from mycroft.util.log import getLogger

__author__ = 'jdorleans'

LOGGER = getLogger(__name__)


class EnclosureArduino:
    """
    Listens to enclosure commands for Mycroft's Arduino.

    Performs the associated command on Arduino by writing on the Serial port.
    """

    def __init__(self, client, writer):
        self.client = client
        self.writer = writer
        self.__init_events()

    def __init_events(self):
        self.client.on('enclosure.system.mute', self.mute)
        self.client.on('enclosure.system.unmute', self.unmute)
        self.client.on('enclosure.system.blink', self.blink)

    def mute(self, event=None):
        self.writer.write("system.mute")

    def unmute(self, event=None):
        self.writer.write("system.unmute")

    def blink(self, event=None):
        times = 1
        if event and event.metadata:
            times = event.metadata.get("times", times)
        self.writer.write("system.blink=" + str(times))
