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


import sys
from Queue import Queue
from threading import Thread

import serial

from mycroft.client.enclosure.arduino import EnclosureArduino
from mycroft.client.enclosure.eyes import EnclosureEyes
from mycroft.client.enclosure.mouth import EnclosureMouth
from mycroft.configuration.config import ConfigurationManager
from mycroft.messagebus.client.ws import WebsocketClient
from mycroft.messagebus.message import Message
from mycroft.util import kill
from mycroft.util.log import getLogger

__author__ = 'aatchison + jdorleans'

LOGGER = getLogger("EnclosureClient")


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
                    LOGGER.info("Reading: " + data)
            except Exception as e:
                LOGGER.error("Reading error: {0}".format(e))

    def process(self, data):
        if "mycroft.stop" in data:
            self.client.emit(Message("mycroft.stop"))
            kill(['mimic'])  # TODO - Refactoring in favor of Mycroft Stop

    def stop(self):
        self.alive = False
        self.join()


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
                LOGGER.info("Writing: " + cmd)
                self.commands.task_done()
            except Exception as e:
                LOGGER.error("Writing error: {0}".format(e))

    def write(self, command):
        self.commands.put(str(command))

    def stop(self):
        self.alive = False
        self.join()


class Enclosure:
    """
    Serves as a communication interface between Arduino and Mycroft Core.

    ``Enclosure`` initializes and aggregates all enclosures implementation.

    E.g. ``EnclosureEyes``, ``EnclosureMouth`` and ``EnclosureArduino``

    It also listens to the basis events in order to perform those core actions
    on the unit.

    E.g. Start and Stop talk animation
    """

    def __init__(self):
        self.__init_serial()
        self.client = WebsocketClient()
        self.reader = EnclosureReader(self.serial, self.client)
        self.writer = EnclosureWriter(self.serial, self.client)
        self.eyes = EnclosureEyes(self.client, self.writer)
        self.mouth = EnclosureMouth(self.client, self.writer)
        self.system = EnclosureArduino(self.client, self.writer)
        self.__register_events()

    def __init_serial(self):
        try:
            self.config = ConfigurationManager.get().get("enclosure")
            self.port = self.config.get("port")
            self.rate = int(self.config.get("rate"))
            self.timeout = int(self.config.get("timeout"))
            self.serial = serial.serial_for_url(
                url=self.port, baudrate=self.rate, timeout=self.timeout)
            LOGGER.info(
                "Connected to: " + self.port + " rate: " + str(self.rate) +
                " timeout: " + str(self.timeout))
        except:
            LOGGER.error(
                "It is not possible to connect to serial port: " + self.port)
            raise

    def __register_events(self):
        self.client.on('mycroft.paired', self.__update_events)
        self.client.on('recognizer_loop:wakeword', self.eyes.blink)
        self.__register_mouth_events()

    def __register_mouth_events(self):
        self.client.on('recognizer_loop:listening', self.mouth.listen)
        self.client.on('recognizer_loop:audio_output_start', self.mouth.talk)
        self.client.on('recognizer_loop:audio_output_end', self.mouth.reset)

    def __remove_mouth_events(self):
        self.client.remove('recognizer_loop:listening', self.mouth.listen)
        self.client.remove('recognizer_loop:audio_output_start',
                           self.mouth.talk)
        self.client.remove('recognizer_loop:audio_output_end',
                           self.mouth.reset)
        self.mouth.reset()

    def __update_events(self, event=None):
        if event and event.metadata:
            if event.metadata.get('paired', False):
                self.__register_mouth_events()
            else:
                self.__remove_mouth_events()

    def run(self):
        try:
            self.client.run_forever()
        except Exception as e:
            LOGGER.error("Client error: {0}".format(e))
            self.stop()

    def stop(self):
        self.writer.stop()
        self.reader.stop()
        self.serial.close()


def main():
    try:
        Enclosure().run()
    finally:
        sys.exit()


if __name__ == "__main__":
    main()
