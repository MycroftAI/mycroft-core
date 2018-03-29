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
import subprocess
import time
import sys
from alsaaudio import Mixer
from threading import Thread, Timer

import serial

import mycroft.dialog
from mycroft.api import has_been_paired
from mycroft.client.enclosure.arduino import EnclosureArduino
from mycroft.client.enclosure.display_manager import \
    initiate_display_manager_ws
from mycroft.client.enclosure.eyes import EnclosureEyes
from mycroft.client.enclosure.mouth import EnclosureMouth
from mycroft.client.enclosure.weather import EnclosureWeather
from mycroft.configuration import Configuration, LocalConf, USER_CONFIG
from mycroft.messagebus.client.ws import WebsocketClient
from mycroft.messagebus.message import Message
from mycroft.util import play_wav, create_signal, connected, \
    wait_while_speaking
from mycroft.util.audio_test import record
from mycroft.util.log import LOG
if sys.version_info[0] < 3:
    from Queue import Queue
else:
    from queue import Queue


class EnclosureReader(Thread):
    """
    Reads data from Serial port.

    Listens to all commands sent by Arduino that must be be performed on
    Mycroft Core.

    E.g. Mycroft Stop Feature
        #. Arduino sends a Stop command after a button press on a Mycroft unit
        #. ``EnclosureReader`` captures the Stop command
        #. Notify all Mycroft Core processes (e.g. skills) to be stopped

    Note: A command is identified by a line break
    """

    def __init__(self, serial, ws, lang=None):
        super(EnclosureReader, self).__init__(target=self.read)
        self.alive = True
        self.daemon = True
        self.serial = serial
        self.ws = ws
        self.lang = lang or 'en-us'
        self.start()

    def read(self):
        while self.alive:
            try:
                data = self.serial.readline()[:-2]
                if data:
                    self.process(data)
            except Exception as e:
                LOG.error("Reading error: {0}".format(e))

    def process(self, data):
        # TODO: Look into removing this emit altogether.
        # We need to check if any other serial bus messages
        # are handled by other parts of the code
        if "mycroft.stop" not in data:
            self.ws.emit(Message(data))

        if "Command: system.version" in data:
            # This happens in response to the "system.version" message
            # sent during the construction of Enclosure()
            self.ws.emit(Message("enclosure.started"))

        if "mycroft.stop" in data:
            if has_been_paired():
                create_signal('buttonPress')
                self.ws.emit(Message("mycroft.stop"))

        if "volume.up" in data:
            self.ws.emit(Message("mycroft.volume.increase",
                                 {'play_sound': True}))

        if "volume.down" in data:
            self.ws.emit(Message("mycroft.volume.decrease",
                                 {'play_sound': True}))

        if "system.test.begin" in data:
            self.ws.emit(Message('recognizer_loop:sleep'))

        if "system.test.end" in data:
            self.ws.emit(Message('recognizer_loop:wake_up'))

        if "mic.test" in data:
            mixer = Mixer()
            prev_vol = mixer.getvolume()[0]
            mixer.setvolume(35)
            self.ws.emit(Message("speak", {
                'utterance': "I am testing one two three"}))

            time.sleep(0.5)  # Prevents recording the loud button press
            record("/tmp/test.wav", 3.0)
            mixer.setvolume(prev_vol)
            play_wav("/tmp/test.wav").communicate()

            # Test audio muting on arduino
            subprocess.call('speaker-test -P 10 -l 0 -s 1', shell=True)

        if "unit.shutdown" in data:
            # Eyes to soft gray on shutdown
            self.ws.emit(Message("enclosure.eyes.color",
                                 {'r': 70, 'g': 65, 'b': 69}))
            self.ws.emit(
                Message("enclosure.eyes.timedspin",
                        {'length': 12000}))
            self.ws.emit(Message("enclosure.mouth.reset"))
            time.sleep(0.5)  # give the system time to pass the message
            self.ws.emit(Message("system.shutdown"))

        if "unit.reboot" in data:
            # Eyes to soft gray on reboot
            self.ws.emit(Message("enclosure.eyes.color",
                                 {'r': 70, 'g': 65, 'b': 69}))
            self.ws.emit(Message("enclosure.eyes.spin"))
            self.ws.emit(Message("enclosure.mouth.reset"))
            time.sleep(0.5)  # give the system time to pass the message
            self.ws.emit(Message("system.reboot"))

        if "unit.setwifi" in data:
            self.ws.emit(Message("system.wifi.setup", {'lang': self.lang}))

        if "unit.factory-reset" in data:
            self.ws.emit(Message("speak", {
                'utterance': mycroft.dialog.get("reset to factory defaults")}))
            subprocess.call(
                'rm ~/.mycroft/identity/identity2.json',
                shell=True)
            self.ws.emit(Message("system.wifi.reset"))
            self.ws.emit(Message("system.ssh.disable"))
            wait_while_speaking()
            self.ws.emit(Message("enclosure.mouth.reset"))
            self.ws.emit(Message("enclosure.eyes.spin"))
            self.ws.emit(Message("enclosure.mouth.reset"))
            time.sleep(5)  # give the system time to process all messages
            self.ws.emit(Message("system.reboot"))

        if "unit.enable-ssh" in data:
            # This is handled by the wifi client
            self.ws.emit(Message("system.ssh.enable"))
            self.ws.emit(Message("speak", {
                'utterance': mycroft.dialog.get("ssh enabled")}))

        if "unit.disable-ssh" in data:
            # This is handled by the wifi client
            self.ws.emit(Message("system.ssh.disable"))
            self.ws.emit(Message("speak", {
                'utterance': mycroft.dialog.get("ssh disabled")}))

        if "unit.enable-learning" in data or "unit.disable-learning" in data:
            enable = 'enable' in data
            word = 'enabled' if enable else 'disabled'

            LOG.info("Setting opt_in to: " + word)
            new_config = {'opt_in': enable}
            user_config = LocalConf(USER_CONFIG)
            user_config.merge(new_config)
            user_config.store()

            self.ws.emit(Message("speak", {
                'utterance': mycroft.dialog.get("learning " + word)}))

    def stop(self):
        self.alive = False


class EnclosureWriter(Thread):
    """
    Writes data to Serial port.
        #. Enqueues all commands received from Mycroft enclosures
           implementation
        #. Process them on the received order by writing on the Serial port

    E.g. Displaying a text on Mycroft's Mouth
        #. ``EnclosureMouth`` sends a text command
        #. ``EnclosureWriter`` captures and enqueue the command
        #. ``EnclosureWriter`` removes the next command from the queue
        #. ``EnclosureWriter`` writes the command to Serial port

    Note: A command has to end with a line break
    """

    def __init__(self, serial, ws, size=16):
        super(EnclosureWriter, self).__init__(target=self.flush)
        self.alive = True
        self.daemon = True
        self.serial = serial
        self.ws = ws
        self.commands = Queue(size)
        self.start()

    def flush(self):
        while self.alive:
            try:
                cmd = self.commands.get()
                self.serial.write(cmd + '\n')
                self.commands.task_done()
            except Exception as e:
                LOG.error("Writing error: {0}".format(e))

    def write(self, command):
        self.commands.put(str(command))

    def stop(self):
        self.alive = False


class Enclosure(object):
    """
    Serves as a communication interface between Arduino and Mycroft Core.

    ``Enclosure`` initializes and aggregates all enclosures implementation.

    E.g. ``EnclosureEyes``, ``EnclosureMouth`` and ``EnclosureArduino``

    It also listens to the basis events in order to perform those core actions
    on the unit.

    E.g. Start and Stop talk animation
    """

    _last_internet_notification = 0

    def __init__(self):
        self.ws = WebsocketClient()

        Configuration.init(self.ws)

        global_config = Configuration.get()
        self.lang = global_config['lang']
        self.config = global_config.get("enclosure")

        self.__init_serial()
        self.reader = EnclosureReader(self.serial, self.ws, self.lang)
        self.writer = EnclosureWriter(self.serial, self.ws)

        # Prepare to receive message when the Arduino responds to the
        # following "system.version"
        self.ws.on("enclosure.started", self.on_arduino_responded)
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
        self.ws.on("enclosure.notify.no_internet", self.on_no_internet)

        # initiates the web sockets on display manager
        # NOTE: this is a temporary place to initiate display manager sockets
        initiate_display_manager_ws()

    def on_arduino_responded(self, event=None):
        self.eyes = EnclosureEyes(self.ws, self.writer)
        self.mouth = EnclosureMouth(self.ws, self.writer)
        self.system = EnclosureArduino(self.ws, self.writer)
        self.weather = EnclosureWeather(self.ws, self.writer)
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

        Timer(60, self._hack_check_for_duplicates).start()

    def on_no_internet(self, event=None):
        if connected():
            # One last check to see if connection was established
            return

        if time.time() - Enclosure._last_internet_notification < 30:
            # don't bother the user with multiple notifications with 30 secs
            return

        Enclosure._last_internet_notification = time.time()

        # TODO: This should go into EnclosureMark1 subclass of Enclosure.
        if has_been_paired():
            # Handle the translation within that code.
            self.ws.emit(Message("speak", {
                'utterance': "This device is not connected to the Internet. "
                             "Either plug in a network cable or hold the "
                             "button on top for two seconds, then select "
                             "wifi from the menu"}))
        else:
            # enter wifi-setup mode automatically
            self.ws.emit(Message('system.wifi.setup', {'lang': self.lang}))

    def __init_serial(self):
        try:
            self.port = self.config.get("port")
            self.rate = self.config.get("rate")
            self.timeout = self.config.get("timeout")
            self.serial = serial.serial_for_url(
                url=self.port, baudrate=self.rate, timeout=self.timeout)
            LOG.info("Connected to: %s rate: %s timeout: %s" %
                     (self.port, self.rate, self.timeout))
        except:
            LOG.error("Impossible to connect to serial port: "+str(self.port))
            raise

    def __register_events(self):
        self.ws.on('enclosure.mouth.events.activate',
                   self.__register_mouth_events)
        self.ws.on('enclosure.mouth.events.deactivate',
                   self.__remove_mouth_events)
        self.ws.on('enclosure.reset',
                   self.__reset)
        self.__register_mouth_events()

    def __register_mouth_events(self, event=None):
        self.ws.on('recognizer_loop:record_begin', self.mouth.listen)
        self.ws.on('recognizer_loop:record_end', self.mouth.reset)
        self.ws.on('recognizer_loop:audio_output_start', self.mouth.talk)
        self.ws.on('recognizer_loop:audio_output_end', self.mouth.reset)

    def __remove_mouth_events(self, event=None):
        self.ws.remove('recognizer_loop:record_begin', self.mouth.listen)
        self.ws.remove('recognizer_loop:record_end', self.mouth.reset)
        self.ws.remove('recognizer_loop:audio_output_start',
                       self.mouth.talk)
        self.ws.remove('recognizer_loop:audio_output_end',
                       self.mouth.reset)

    def __reset(self, event=None):
        # Reset both the mouth and the eye elements to indicate the unit is
        # ready for input.
        self.writer.write("eyes.reset")
        self.writer.write("mouth.reset")

    def speak(self, text):
        self.ws.emit(Message("speak", {'utterance': text}))

    def run(self):
        try:
            self.ws.run_forever()
        except Exception as e:
            LOG.error("Error: {0}".format(e))
            self.stop()

    def check_for_response(self):
        if not self.arduino_responded:
            # There is nothing on the other end of the serial port
            # close these serial-port readers and this process
            self.writer.stop()
            self.reader.stop()
            self.serial.close()
            self.ws.close()

    def _handle_pairing_complete(self, Message):
        """
            Handler for 'mycroft.paired', unmutes the mic after the pairing is
            complete.
        """
        self.ws.emit(Message("mycroft.mic.unmute"))

    def _do_net_check(self):
        # TODO: This should live in the derived Enclosure, e.g. Enclosure_Mark1
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

                # TODO: This logic should be in Enclosure_Mark1
                # TODO: Enclosure/localization

                # Don't listen to mic during this out-of-box experience
                self.ws.emit(Message("mycroft.mic.mute"))
                # Setup handler to unmute mic at the end of on boarding
                # i.e. after pairing is complete
                self.ws.once('mycroft.paired', self._handle_pairing_complete)

                self.speak(mycroft.dialog.get('mycroft.intro'))
                wait_while_speaking()
                time.sleep(2)  # a pause sounds better than just jumping in

                # Kick off wifi-setup automatically
                data = {'allow_timeout': False, 'lang': self.lang}
                self.ws.emit(Message('system.wifi.setup', data))

    def _hack_check_for_duplicates(self):
        # TEMPORARY HACK:  Look for multiple instance of the
        # mycroft-speech-client and/or mycroft-skills services, which could
        # happen when upgrading a shipping Mark 1 from release 0.8.17 or
        # before.  When found, force the unit to reboot.
        import psutil

        LOG.info("Hack to check for duplicate service instances")

        count_instances = 0
        needs_reboot = False
        for process in psutil.process_iter():
            if process.cmdline() == ['python2.7',
                                     '/usr/local/bin/mycroft-speech-client']:
                count_instances += 1
        if (count_instances > 1):
            LOG.info("Duplicate mycroft-speech-client found")
            needs_reboot = True

        count_instances = 0
        for process in psutil.process_iter():
            if process.cmdline() == ['python2.7',
                                     '/usr/local/bin/mycroft-skills']:
                count_instances += 1
        if (count_instances > 1):
            LOG.info("Duplicate mycroft-skills found")
            needs_reboot = True

        if needs_reboot:
            LOG.info("Hack reboot...")
            self.reader.process("unit.reboot")
            self.ws.emit(Message("enclosure.eyes.spin"))
            self.ws.emit(Message("enclosure.mouth.reset"))
        # END HACK
        # TODO: Remove this hack ASAP
