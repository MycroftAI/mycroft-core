# Copyright 2017 Mycroft AI Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

"""
NOTE: this is dead code! do not use!

This file is only present to ensure backwards compatibility
in case someone is importing from here

This is only meant for 3rd party code expecting ovos-core
to be a drop in replacement for mycroft-core

TODO: consider importing from PHAL if it's compatible
"""

import subprocess
import time
from alsaaudio import Mixer
from threading import Thread, Timer

import serial

import xdg.BaseDirectory

import mycroft.dialog
from mycroft.client.enclosure.base import Enclosure
from mycroft.api import has_been_paired
from mycroft.audio import wait_while_speaking
from mycroft.client.enclosure.mark1.arduino import EnclosureArduino
from mycroft.client.enclosure.mark1.eyes import EnclosureEyes
from mycroft.client.enclosure.mark1.mouth import EnclosureMouth
from mycroft.configuration import LocalConf, USER_CONFIG
from mycroft.messagebus.message import Message
from mycroft.util import play_wav, create_signal, connected, check_for_signal
from mycroft.util.audio_test import record
from mycroft.util.log import LOG
from queue import Queue
from mycroft.util.file_utils import get_temp_path


# The Mark 1 hardware consists of a Raspberry Pi main CPU which is connected
# to an Arduino over the serial port.  A custom serial protocol sends
# commands to control various visual elements which are controlled by the
# Arduino (e.g. two circular rings of RGB LEDs; and four 8x8 white LEDs).
#
# The Arduino can also send back notifications in response to either
# pressing or turning a rotary encoder.


class EnclosureReader(Thread):
    """
    Reads data from Serial port.

    Listens to all commands sent by Arduino that must be be performed on
    Mycroft Core.

    E.g. Mycroft Stop Feature
        # . Arduino sends a Stop command after a button press on a Mycroft unit
        # . ``EnclosureReader`` captures the Stop command
        # . Notify all Mycroft Core processes (e.g. skills) to be stopped

    Note: A command is identified by a line break
    """

    def __init__(self, serial, bus, lang=None):
        super(EnclosureReader, self).__init__(target=self.read)
        self.alive = True
        self.daemon = True
        self.serial = serial
        self.bus = bus
        self.lang = lang or 'en-us'
        self.start()

        # Notifications from mycroft-core
        self.bus.on("mycroft.stop.handled", self.on_stop_handled)

    def read(self):
        while self.alive:
            try:
                data = self.serial.readline()[:-2]
                if data:
                    try:
                        data_str = data.decode()
                    except UnicodeError as e:
                        data_str = data.decode('utf-8', errors='replace')
                        LOG.warning('Invalid characters in response from '
                                    ' enclosure: {}'.format(repr(e)))
                    self.process(data_str)
            except Exception as e:
                LOG.error("Reading error: {0}".format(e))

    def on_stop_handled(self, event):
        # A skill performed a stop
        check_for_signal('buttonPress')

    def process(self, data):
        # TODO: Look into removing this emit altogether.
        # We need to check if any other serial bus messages
        # are handled by other parts of the code
        if "mycroft.stop" not in data:
            self.bus.emit(Message(data))

        if "Command: system.version" in data:
            # This happens in response to the "system.version" message
            # sent during the construction of Enclosure()
            self.bus.emit(Message("enclosure.started"))

        if "mycroft.stop" in data:
            if has_been_paired():
                create_signal('buttonPress')
                self.bus.emit(Message("mycroft.stop"))

        if "volume.up" in data:
            self.bus.emit(Message("mycroft.volume.increase",
                                  {'play_sound': True}))

        if "volume.down" in data:
            self.bus.emit(Message("mycroft.volume.decrease",
                                  {'play_sound': True}))

        if "system.test.begin" in data:
            self.bus.emit(Message('recognizer_loop:sleep'))

        if "system.test.end" in data:
            self.bus.emit(Message('recognizer_loop:wake_up'))

        if "mic.test" in data:
            mixer = Mixer()
            prev_vol = mixer.getvolume()[0]
            mixer.setvolume(35)
            self.bus.emit(Message("speak", {
                'utterance': "I am testing one two three"}))

            time.sleep(0.5)  # Prevents recording the loud button press
            record(get_temp_path('test.wav', 3.0))
            mixer.setvolume(prev_vol)
            play_wav(get_temp_path('test.wav')).communicate()

            # Test audio muting on arduino
            subprocess.call('speaker-test -P 10 -l 0 -s 1', shell=True)

        if "unit.shutdown" in data:
            # Eyes to soft gray on shutdown
            self.bus.emit(Message("enclosure.eyes.color",
                                  {'r': 70, 'g': 65, 'b': 69}))
            self.bus.emit(
                Message("enclosure.eyes.timedspin",
                        {'length': 12000}))
            self.bus.emit(Message("enclosure.mouth.reset"))
            time.sleep(0.5)  # give the system time to pass the message
            self.bus.emit(Message("system.shutdown"))

        if "unit.reboot" in data:
            # Eyes to soft gray on reboot
            self.bus.emit(Message("enclosure.eyes.color",
                                  {'r': 70, 'g': 65, 'b': 69}))
            self.bus.emit(Message("enclosure.eyes.spin"))
            self.bus.emit(Message("enclosure.mouth.reset"))
            time.sleep(0.5)  # give the system time to pass the message
            self.bus.emit(Message("system.reboot"))

        if "unit.setwifi" in data:
            self.bus.emit(Message("system.wifi.setup", {'lang': self.lang}))

        if "unit.factory-reset" in data:
            self.bus.emit(Message("speak", {
                'utterance': mycroft.dialog.get("reset to factory defaults")}))
            subprocess.call(
                (f'rm {xdg.BaseDirectory.save_config_path("mycroft")}'
                 '/mycroft/identity/identity2.json'),
                shell=True)
            subprocess.call(
                'rm ~/.mycroft/identity/identity2.json',
                shell=True)
            self.bus.emit(Message("system.wifi.reset"))
            self.bus.emit(Message("system.ssh.disable"))
            wait_while_speaking()
            self.bus.emit(Message("enclosure.mouth.reset"))
            self.bus.emit(Message("enclosure.eyes.spin"))
            self.bus.emit(Message("enclosure.mouth.reset"))
            time.sleep(5)  # give the system time to process all messages
            self.bus.emit(Message("system.reboot"))

        if "unit.enable-ssh" in data:
            # This is handled by the wifi client
            self.bus.emit(Message("system.ssh.enable"))
            self.bus.emit(Message("speak", {
                'utterance': mycroft.dialog.get("ssh enabled")}))

        if "unit.disable-ssh" in data:
            # This is handled by the wifi client
            self.bus.emit(Message("system.ssh.disable"))
            self.bus.emit(Message("speak", {
                'utterance': mycroft.dialog.get("ssh disabled")}))

        if "unit.enable-learning" in data or "unit.disable-learning" in data:
            enable = 'enable' in data
            word = 'enabled' if enable else 'disabled'

            LOG.info("Setting opt_in to: " + word)
            new_config = {'opt_in': enable}
            user_config = LocalConf(USER_CONFIG)
            user_config.merge(new_config)
            user_config.store()

            self.bus.emit(Message("speak", {
                'utterance': mycroft.dialog.get("learning " + word)}))

    def stop(self):
        self.alive = False


class EnclosureWriter(Thread):
    """
    Writes data to Serial port.
        # . Enqueues all commands received from Mycroft enclosures
           implementation
        # . Process them on the received order by writing on the Serial port

    E.g. Displaying a text on Mycroft's Mouth
        # . ``EnclosureMouth`` sends a text command
        # . ``EnclosureWriter`` captures and enqueue the command
        # . ``EnclosureWriter`` removes the next command from the queue
        # . ``EnclosureWriter`` writes the command to Serial port

    Note: A command has to end with a line break
    """

    def __init__(self, serial, bus, size=16):
        super(EnclosureWriter, self).__init__(target=self.flush)
        self.alive = True
        self.daemon = True
        self.serial = serial
        self.bus = bus
        self.commands = Queue(size)
        self.start()

    def flush(self):
        while self.alive:
            try:
                cmd = self.commands.get() + '\n'
                self.serial.write(cmd.encode())
                self.commands.task_done()
            except Exception as e:
                LOG.error("Writing error: {0}".format(e))

    def write(self, command):
        self.commands.put(str(command))

    def stop(self):
        self.alive = False


class EnclosureMark1(Enclosure):
    """
    Serves as a communication interface between Arduino and Mycroft Core.

    ``Enclosure`` initializes and aggregates all enclosures implementation.

    E.g. ``EnclosureEyes``, ``EnclosureMouth`` and ``EnclosureArduino``

    It also listens to the basic events in order to perform those core actions
    on the unit.

    E.g. Start and Stop talk animation
    """

    _last_internet_notification = 0

    def __init__(self):
        super().__init__()

        self.__init_serial()
        self.reader = EnclosureReader(self.serial, self.bus, self.lang)
        self.writer = EnclosureWriter(self.serial, self.bus)

        # Prepare to receive message when the Arduino responds to the
        # following "system.version"
        self.bus.on("enclosure.started", self.on_arduino_responded)
        self.arduino_responded = False
        # Send a message to the Arduino across the serial line asking
        # for a reply with version info.
        self.writer.write("system.version")
        # Start a 5 second timer.  If the serial port hasn't received
        # any acknowledgement of the "system.version" within those
        # 5 seconds, assume there is nothing on the other end (e.g.
        # we aren't running a Mark 1 with an Arduino)
        Timer(5, self.check_for_response).start()

        # Notifications from mycroft-core
        self.bus.on("enclosure.notify.no_internet", self.on_no_internet)

    def on_arduino_responded(self, event=None):
        self.eyes = EnclosureEyes(self.bus, self.writer)
        self.mouth = EnclosureMouth(self.bus, self.writer)
        self.system = EnclosureArduino(self.bus, self.writer)
        self.__register_events()
        self.__reset()
        self.arduino_responded = True

        # verify internet connection and prompt user on bootup if needed
        if not connected():
            # We delay this for several seconds to ensure that the other
            # clients are up and connected to the messagebus in order to
            # receive the "speak".  This was sometimes happening too
            # quickly and the user wasn't notified what to do.
            Timer(5, self._do_net_check).start()

    def on_no_internet(self, event=None):
        if connected():
            # One last check to see if connection was established
            return

        if time.time() - Enclosure._last_internet_notification < 30:
            # don't bother the user with multiple notifications with 30 secs
            return

        Enclosure._last_internet_notification = time.time()

        if has_been_paired():
            # Handle the translation within that code.
            self.bus.emit(Message("speak", {
                'utterance': "This device is not connected to the Internet. "
                             "Either plug in a network cable or hold the "
                             "button on top for two seconds, then select "
                             "wifi from the menu"}))
        else:
            # enter wifi-setup mode automatically
            self.bus.emit(Message('system.wifi.setup', {'lang': self.lang}))

    def __init_serial(self):
        try:
            self.port = self.config.get("port")
            self.rate = self.config.get("rate")
            self.timeout = self.config.get("timeout")
            self.serial = serial.serial_for_url(
                url=self.port, baudrate=self.rate, timeout=self.timeout)
            LOG.info("Connected to: %s rate: %s timeout: %s" %
                     (self.port, self.rate, self.timeout))
        except Exception:
            LOG.error("Impossible to connect to serial port: " +
                      str(self.port))
            raise

    def __register_events(self):
        self.bus.on('enclosure.mouth.events.activate',
                    self.__register_mouth_events)
        self.bus.on('enclosure.mouth.events.deactivate',
                    self.__remove_mouth_events)
        self.bus.on('enclosure.reset',
                    self.__reset)
        self.__register_mouth_events()

    def __register_mouth_events(self, event=None):
        self.bus.on('recognizer_loop:record_begin', self.mouth.listen)
        self.bus.on('recognizer_loop:record_end', self.mouth.reset)
        self.bus.on('recognizer_loop:audio_output_start', self.mouth.talk)
        self.bus.on('recognizer_loop:audio_output_end', self.mouth.reset)

    def __remove_mouth_events(self, event=None):
        self.bus.remove('recognizer_loop:record_begin', self.mouth.listen)
        self.bus.remove('recognizer_loop:record_end', self.mouth.reset)
        self.bus.remove('recognizer_loop:audio_output_start',
                        self.mouth.talk)
        self.bus.remove('recognizer_loop:audio_output_end',
                        self.mouth.reset)

    def __reset(self, event=None):
        # Reset both the mouth and the eye elements to indicate the unit is
        # ready for input.
        self.writer.write("eyes.reset")
        self.writer.write("mouth.reset")

    def speak(self, text):
        self.bus.emit(Message("speak", {'utterance': text}))

    def check_for_response(self):
        if not self.arduino_responded:
            # There is nothing on the other end of the serial port
            # close these serial-port readers and this process
            self.writer.stop()
            self.reader.stop()
            self.serial.close()
            self.bus.close()

    def _handle_pairing_complete(self, Message):
        """
            Handler for 'mycroft.paired', unmutes the mic after the pairing is
            complete.
        """
        self.bus.emit(Message("mycroft.mic.unmute"))

    def _do_net_check(self):
        LOG.info("Checking internet connection")
        if not connected():  # and self.conn_monitor is None:
            if has_been_paired():
                # TODO: Enclosure/localization
                self.speak("This unit is not connected to the Internet. "
                           "Either plug in a network cable or hold the "
                           "button on top for two seconds, then select "
                           "wifi from the menu")
            else:
                # Begin the unit startup process, this is the first time it
                # is being run with factory defaults.

                # TODO: Enclosure/localization

                # Don't listen to mic during this out-of-box experience
                self.bus.emit(Message("mycroft.mic.mute"))
                # Setup handler to unmute mic at the end of on boarding
                # i.e. after pairing is complete
                self.bus.once('mycroft.paired', self._handle_pairing_complete)

                self.speak(mycroft.dialog.get('mycroft.intro'))
                wait_while_speaking()
                time.sleep(2)  # a pause sounds better than just jumping in

                # Kick off wifi-setup automatically
                data = {'allow_timeout': False, 'lang': self.lang}
                self.bus.emit(Message('system.wifi.setup', data))
