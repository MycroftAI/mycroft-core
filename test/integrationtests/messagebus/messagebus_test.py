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
"""This is a unittest for the message buss

It's important to note that this requires this test to run mycroft service
to test the buss.  It is not expected that the service be already running
when the tests are ran.
"""
import time
import unittest
from subprocess import Popen, call
from threading import Thread

from mycroft.messagebus.client import MessageBusClient
from mycroft.messagebus.message import Message


class TestMessagebusMethods(unittest.TestCase):
    """This class is for testing the messsagebus.

    It currently only tests send and receive.  The tests could include
    more.
    """

    def setUp(self):
        """
        This sets up for testing the message buss

        This requires starting the mycroft service and creating two
        WebsocketClient object to talk with eachother.  Not this is
        threaded and will require cleanup
        """
        # start the mycroft service. and get the pid of the script.
        self.pid = Popen(["python3", "-m", "mycroft.messagebus.service"]).pid
        # Create the two web clients
        self.ws1 = MessageBusClient()
        self.ws2 = MessageBusClient()
        # init the flags for handler's
        self.handle1 = False
        self.handle2 = False
        # Start threads to handle websockets
        Thread(target=self.ws1.run_forever).start()
        Thread(target=self.ws2.run_forever).start()
        # Setup handlers for each of the messages.
        self.ws1.on('ws1.message', self.onHandle1)
        self.ws2.on('ws2.message', self.onHandle2)

    def onHandle1(self, event):
        """This is the handler for ws1.message

        This for now simply sets a flag to true when received.

        Args:
            event(Message): this is the message received
        """
        self.handle1 = True

    def onHandle2(self, event):
        """This is the handler for ws2.message

        This for now simply sets a flag to true when received.

        Args:
            event(Message): this is the message received
        """
        self.handle2 = True

    def tearDown(self):
        """This is the clean up for the tests

        This will close the websockets ending the threads then kill the
        mycroft service that was started in setUp.
        """
        self.ws1.close()
        self.ws2.close()
        retcode = call(["kill", "-9", str(self.pid)])

    def test_ClientServer(self):
        """This is the test to send a message from each of the websockets
        to the other.
        """
        # Send the messages
        self.ws2.emit(Message('ws1.message'))
        self.ws1.emit(Message('ws2.message'))
        # allow time for messages to be processed
        time.sleep(0.2)
        # Check that both of the handlers were called.
        self.assertTrue(self.handle1)
        self.assertTrue(self.handle2)


if __name__ == '__main__':
    """This is to start the testing"""
    unittest.main()
