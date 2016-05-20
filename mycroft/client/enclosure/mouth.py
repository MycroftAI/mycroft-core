from mycroft.util.log import getLogger

__author__ = 'jdorleans'

LOGGER = getLogger(__name__)


class EnclosureMouth:
    """
    Listens to enclosure commands for Mycroft's Mouth.

    Performs the associated command on Arduino by writing on the Serial port.
    """

    def __init__(self, client, writer):
        self.client = client
        self.writer = writer
        self.__init_events()

    def __init_events(self):
        self.client.on('enclosure.mouth.reset', self.reset)
        self.client.on('enclosure.mouth.talk', self.talk)
        self.client.on('enclosure.mouth.think', self.think)
        self.client.on('enclosure.mouth.listen', self.listen)
        self.client.on('enclosure.mouth.smile', self.smile)
        self.client.on('enclosure.mouth.text', self.text)

    def reset(self, event=None):
        self.writer.write("mouth.reset")

    def talk(self, event=None):
        self.writer.write("mouth.talk")

    def think(self, event=None):
        self.writer.write("mouth.think")

    def listen(self, event=None):
        self.writer.write("mouth.listen")

    def smile(self, event=None):
        self.writer.write("mouth.smile")

    def text(self, event=None):
        text = ""
        if event and event.metadata:
            text = event.metadata.get("text", text)
        self.writer.write("mouth.text=" + text)
