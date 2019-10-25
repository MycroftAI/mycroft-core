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
import sys
import json

from websocket import create_connection

from mycroft.configuration import Configuration
from mycroft.configuration.locations import (DEFAULT_CONFIG, SYSTEM_CONFIG,
                                             USER_CONFIG)
from mycroft.messagebus.client import MessageBusClient
from mycroft.messagebus.message import Message


def main():
    """Main function, will run if executed from command line.

    Sends parameters from commandline.

    Param 1:    message string
    Param 2:    data (json string)
    """
    # Parse the command line
    if len(sys.argv) == 2:
        message_to_send = sys.argv[1]
        data_to_send = {}
    elif len(sys.argv) == 3:
        message_to_send = sys.argv[1]
        try:
            data_to_send = json.loads(sys.argv[2])
        except BaseException:
            print("Second argument must be a JSON string")
            print("Ex: python -m mycroft.messagebus.send speak "
                  "'{\"utterance\" : \"hello\"}'")
            exit()
    else:
        print("Command line interface to the mycroft-core messagebus.")
        print("Usage: python -m mycroft.messagebus.send message")
        print("       python -m mycroft.messagebus.send message JSON-string\n")
        print("Examples: python -m mycroft.messagebus.send system.wifi.setup")
        print("Ex: python -m mycroft.messagebus.send speak "
              "'{\"utterance\" : \"hello\"}'")
        exit()

    send(message_to_send, data_to_send)


def send(message_to_send, data_to_send=None):
    """Send a single message over the websocket.

    Args:
        message_to_send (str): Message to send
        data_to_send (dict): data structure to go along with the
            message, defaults to empty dict.
    """
    data_to_send = data_to_send or {}

    # Calculate the standard Mycroft messagebus websocket address
    config = Configuration.get([DEFAULT_CONFIG,
                                SYSTEM_CONFIG,
                                USER_CONFIG],
                               cache=False)
    config = config.get("websocket")
    url = MessageBusClient.build_url(
        config.get("host"),
        config.get("port"),
        config.get("route"),
        config.get("ssl")
    )

    # Send the provided message/data
    ws = create_connection(url)
    packet = Message(message_to_send, data_to_send).serialize()
    ws.send(packet)
    ws.close()


if __name__ == '__main__':
    try:
        main()
    except IOError:
        print('Could not connect to websocket, no message sent')
