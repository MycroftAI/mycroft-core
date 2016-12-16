# Copyright 2016 Mycroft AI, Inc.
#
# This file is part of Mycroft Core.
#
# Mycroft Core is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Mycroft Core is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with Mycroft Core.  If not, see <http://www.gnu.org/licenses/>.


import subprocess
import time
from Queue import Queue
from alsaaudio import Mixer
from threading import Thread

import serial

from mycroft.client.enclosure.arduino import EnclosureArduino
from mycroft.client.enclosure.eyes import EnclosureEyes
from mycroft.client.enclosure.mouth import EnclosureMouth
from mycroft.client.enclosure.weather import EnclosureWeather
from mycroft.configuration import ConfigurationManager
from mycroft.messagebus.client.ws import WebsocketClient
from mycroft.messagebus.message import Message
from mycroft.util import play_wav, create_signal
from mycroft.util.audio_test import record
from mycroft.util.log import getLogger

__author__ = 'aatchison', 'jdorleans', 'iward'

LOG = getLogger("EnclosureClient")


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

    def __init__(self, serial, client):
        super(EnclosureReader, self).__init__(target=self.read)
        self.alive = True
        self.daemon = True
        self.serial = serial
        self.client = client
        self.start()

    def read(self):
        while self.alive:
            try:
                data = self.serial.readline()[:-2]
                if data:
                    self.process(data)
                    LOG.info("Reading: " + data)
            except Exception as e:
                LOG.error("Reading error: {0}".format(e))

    def process(self, data):
        self.client.emit(Message(data))

        if "mycroft.stop" in data:
            create_signal('buttonPress')
            self.client.emit(Message("mycroft.stop"))

        if "volume.up" in data:
            self.client.emit(
                Message("IncreaseVolumeIntent", {'play_sound': True}))

        if "volume.down" in data:
            self.client.emit(
                Message("DecreaseVolumeIntent", {'play_sound': True}))

        if "system.test.begin" in data:
            self.client.emit(Message('recognizer_loop:sleep'))

        if "system.test.end" in data:
            self.client.emit(Message('recognizer_loop:wake_up'))

        if "mic.test" in data:
            mixer = Mixer()
            prev_vol = mixer.getvolume()[0]
            mixer.setvolume(35)
            self.client.emit(Message("speak", {
                'utterance': "I am testing one two three"}))

            time.sleep(0.5)  # Prevents recording the loud button press
            record("/tmp/test.wav", 3.0)
            mixer.setvolume(prev_vol)
            play_wav("/tmp/test.wav").communicate()

            # Test audio muting on arduino
            subprocess.call('speaker-test -P 10 -l 0 -s 1', shell=True)

        if "unit.shutdown" in data:
            self.client.emit(
                Message("enclosure.eyes.timedspin",
                        {'length': 12000}))
            self.client.emit(Message("enclosure.mouth.reset"))
            subprocess.call('systemctl poweroff -i', shell=True)

        if "unit.reboot" in data:
            self.client.emit(
                Message("enclosure.eyes.spin"))
            self.client.emit(Message("enclosure.mouth.reset"))
            subprocess.call('systemctl reboot -i', shell=True)

        if "unit.setwifi" in data:
            self.client.emit(Message("wifisetup.start"))

        if "unit.factory-reset" in data:
            subprocess.call(
                'rm ~/.mycroft/identity/identity.json',
                shell=True)
            self.client.emit(
                Message("enclosure.eyes.spin"))
            self.client.emit(Message("enclosure.mouth.reset"))
            subprocess.call('systemctl reboot -i', shell=True)

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

    def __init__(self, serial, client, size=16):
        super(EnclosureWriter, self).__init__(target=self.flush)
        self.alive = True
        self.daemon = True
        self.serial = serial
        self.client = client
        self.commands = Queue(size)
        self.start()

    def flush(self):
        while self.alive:
            try:
                cmd = self.commands.get()
                self.serial.write(cmd + '\n')
                LOG.info("Writing: " + cmd)
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

    def __init__(self):
        self.client = WebsocketClient()
        ConfigurationManager.init(self.client)
        self.config = ConfigurationManager.get().get("enclosure")
        self.__init_serial()
        self.reader = EnclosureReader(self.serial, self.client)
        self.writer = EnclosureWriter(self.serial, self.client)
        self.eyes = EnclosureEyes(self.client, self.writer)
        self.mouth = EnclosureMouth(self.client, self.writer)
        self.system = EnclosureArduino(self.client, self.writer)
        self.weather = EnclosureWeather(self.client, self.writer)
        self.__register_events()
        self.update()
        self.test()

    def update(self):
        if self.config.get("update"):
            try:
                self.speak("Upgrading enclosure version")
                subprocess.check_call("/opt/enclosure/upload.sh")
                self.speak("Enclosure update completed")
                ConfigurationManager.save({"enclosure": {"update": False}})
                time.sleep(5)
            except:
                self.speak("I cannot upgrade right now, I'll try later")

    def test(self):
        if self.config.get("test"):
            self.speak("Beginning hardware test")
            self.writer.write("test.begin")
            ConfigurationManager.save({"enclosure": {"test": False}})

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
            LOG.error("Impossible to connect to serial port: " + self.port)
            raise

    def __register_events(self):
        self.client.on('enclosure.mouth.events.activate',
                       self.__register_mouth_events)
        self.client.on('enclosure.mouth.events.deactivate',
                       self.__remove_mouth_events)
        self.__register_mouth_events()

    def __register_mouth_events(self, event=None):
        self.client.on('recognizer_loop:record_begin', self.mouth.listen)
        self.client.on('recognizer_loop:record_end', self.mouth.reset)
        self.client.on('recognizer_loop:audio_output_start', self.mouth.talk)
        self.client.on('recognizer_loop:audio_output_end', self.mouth.reset)

    def __remove_mouth_events(self, event=None):
        self.client.remove('recognizer_loop:record_begin', self.mouth.listen)
        self.client.remove('recognizer_loop:record_end', self.mouth.reset)
        self.client.remove('recognizer_loop:audio_output_start',
                           self.mouth.talk)
        self.client.remove('recognizer_loop:audio_output_end',
                           self.mouth.reset)

    def speak(self, text):
        self.client.emit(Message("speak", {'utterance': text}))

    def run(self):
        try:
            self.client.run_forever()
        except Exception as e:
            LOG.error("Client error: {0}".format(e))
            self.stop()

    def stop(self):
        self.writer.stop()
        self.reader.stop()
        self.serial.close()
        self.client.close()
