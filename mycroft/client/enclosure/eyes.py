from mycroft.util.log import getLogger

__author__ = 'jdorleans'

LOGGER = getLogger(__name__)


class EnclosureEyes:
    """
    Listens to enclosure commands for Mycroft's Eyes.

    Performs the associated command on Arduino by writing on the Serial port.
    """

    def __init__(self, client, writer):
        self.client = client
        self.writer = writer
        self.__init_events()

    def __init_events(self):
        self.client.on('enclosure.eyes.on', self.on)
        self.client.on('enclosure.eyes.off', self.off)
        self.client.on('enclosure.eyes.blink', self.blink)
        self.client.on('enclosure.eyes.narrow', self.narrow)
        self.client.on('enclosure.eyes.look', self.look)
        self.client.on('enclosure.eyes.color', self.color)
        self.client.on('enclosure.eyes.level', self.brightness)

    def on(self, event=None):
        self.writer.write("eyes.on")

    def off(self, event=None):
        self.writer.write("eyes.off")

    def blink(self, event=None):
        side = "b"
        if event and event.metadata:
            side = event.metadata.get("side", side)
        self.writer.write("eyes.blink=" + side)

    def narrow(self, event=None):
        self.writer.write("eyes.narrow")

    def look(self, event=None):
        if event and event.metadata:
            side = event.metadata.get("side", "")
            self.writer.write("eyes.look=" + side)

    def color(self, event=None):
        r, g, b = 255, 255, 255
        if event and event.metadata:
            r = int(event.metadata.get("r"), r)
            g = int(event.metadata.get("g"), g)
            b = int(event.metadata.get("b"), b)
        color = (r * 65536) + (g * 256) + b
        self.writer.write("eyes.color=" + str(color))

    def brightness(self, event=None):
        level = 30
        if event and event.metadata:
            level = event.metadata.get("level", level)
        self.writer.write("eyes.level=" + str(level))
