from time import sleep

import mycroft.dialog
from mycroft.api import has_been_paired
from mycroft.messagebus import Message
from mycroft.util import connected, wait_while_speaking
from mycroft.util.log import LOG


def wait_for_internet_connection():
    while not connected():
        sleep(1)


class EnclosureInternet:
    def __init__(self, core_bus, config):
        self.core_bus = core_bus
        self.config = config

    def check_connection(self):
        """Run wifi setup if an internet connection is not established."""
        LOG.info("Checking internet connection...")
        if connected():
            LOG.info('Enclosure is connected to internet')
        else:
            LOG.info('No internet connection detected; starting wifi setup')
            self._mute_mic()
            self._set_mic_unmute_event()
            if not has_been_paired():
                self._speak_intro()
            self._start_wifi_setup()
            wait_for_internet_connection()
        message = Message(msg_type='enclosure.internet.connected')
        self.core_bus.emit(message)

    def _mute_mic(self):
        """Mute the microphone while wifi setup is running."""
        message = Message("mycroft.mic.mute")
        self.core_bus.emit(message)

    def _speak_intro(self):
        """Send a message to the bus triggering the introduction dialog."""
        message = Message(
            msg_type='speak',
            data=dict(utterance=mycroft.dialog.get('mycroft.intro'))
        )
        self.core_bus.emit(message)
        wait_while_speaking()
        sleep(2)  # a pause sounds better than just jumping in

    def _set_mic_unmute_event(self):
        if not has_been_paired():
            self.core_bus.once('mycroft.paired', self._unmute_mic)
        else:
            self.core_bus.once('enclosure.internet.connected', self._unmute_mic)

    def _start_wifi_setup(self):
        """Send a message to the bus that will start the wifi setup process."""
        message = Message(
            msg_type='system.wifi.setup',
            data=dict(allow_timeout=False, lang=self.config['lang'])
        )
        self.core_bus.emit(message)

    def _unmute_mic(self, _):
        """Turn microphone back on after the pairing is complete."""
        self.core_bus.emit(Message("mycroft.mic.unmute"))
