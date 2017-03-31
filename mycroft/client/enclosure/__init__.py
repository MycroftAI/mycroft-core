# Copyright 2016 Mycroft AI, Inc.
#
# This file is part of Mycroft Core.
#
# Mycroft Core is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Mycroft Core is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Mycroft Core.  If not, see <http://www.gnu.org/licenses/>.


import subprocess
import time
from Queue import Queue
from alsaaudio import Mixer
from threading import Thread, Timer

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

    def __init__(self, serial, ws):
        super(EnclosureReader, self).__init__(target=self.read)
        self.alive = True
        self.daemon = True
        self.serial = serial
        self.ws = ws
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
        self.ws.emit(Message(data))

        if "Command: system.version" in data:
            self.ws.emit(Message("enclosure.start"))

        if "mycroft.stop" in data:
            create_signal('buttonPress')  # FIXME - Must use WS instead
            self.ws.emit(Message("mycroft.stop"))

        if "volume.up" in data:
            self.ws.emit(
                Message("VolumeSkill:IncreaseVolumeIntent",
                        {'play_sound': True}))

        if "volume.down" in data:
            self.ws.emit(
                Message("VolumeSkill:DecreaseVolumeIntent",
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
            self.ws.emit(
                Message("enclosure.eyes.timedspin",
                        {'length': 12000}))
            self.ws.emit(Message("enclosure.mouth.reset"))
            subprocess.call('systemctl poweroff -i', shell=True)

        if "unit.reboot" in data:
            self.ws.emit(
                Message("enclosure.eyes.spin"))
            self.ws.emit(Message("enclosure.mouth.reset"))
            subprocess.call('systemctl reboot -i', shell=True)

        if "unit.setwifi" in data:
            self.ws.emit(Message("mycroft.wifi.start"))

        if "unit.factory-reset" in data:
            subprocess.call(
                'rm ~/.mycroft/identity/identity2.json',
                shell=True)
            self.ws.emit(
                Message("enclosure.eyes.spin"))
            self.ws.emit(Message("enclosure.mouth.reset"))
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
        self.ws = WebsocketClient()
        ConfigurationManager.init(self.ws)
        self.config = ConfigurationManager.get().get("enclosure")
        self.__init_serial()
        self.reader = EnclosureReader(self.serial, self.ws)
        self.writer = EnclosureWriter(self.serial, self.ws)
        self.writer.write("system.version")
        self.ws.on("enclosure.start", self.start)
        self.started = False
        Timer(5, self.stop).start()  # WHY? This at least
        # needs an explanation, this is non-obvious behavior

    def start(self, event=None):
        self.eyes = EnclosureEyes(self.ws, self.writer)
        self.mouth = EnclosureMouth(self.ws, self.writer)
        self.system = EnclosureArduino(self.ws, self.writer)
        self.weather = EnclosureWeather(self.ws, self.writer)
        self.__register_events()
        self.__reset()
        self.started = True

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

    def stop(self):
        if not self.started:
            self.writer.stop()
            self.reader.stop()
            self.serial.close()
            self.ws.close()
