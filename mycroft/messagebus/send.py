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
from mycroft.messagebus.client.ws import WebsocketClient
from mycroft.messagebus.message import Message
from mycroft.configuration import ConfigurationManager
from websocket import create_connection

# Parse the command line
if len(sys.argv) == 2:
    messageToSend = sys.argv[1]
    dataToSend = {}
elif len(sys.argv) == 3:
    messageToSend = sys.argv[1]
    try:
        dataToSend = json.loads(sys.argv[2])
    except BaseException:
        print "Second argument must be a JSON string"
        print "Ex: python -m mycroft.messagebus.send speak " \
            "'{\"utterance\" : \"hello\"}'"
        exit()
else:
    print "Command line interface to the mycroft-core messagebus."
    print "Usage:    python -m mycroft.messagebus.send message"
    print "          python -m mycroft.messagebus.send message JSON-string\n"
    print "Examples: python -m mycroft.messagebus.send mycroft.wifi.start"
    print "Ex: python -m mycroft.messagebus.send speak " \
        "'{\"utterance\" : \"hello\"}'"
    exit()


# Calculate the standard Mycroft messagebus websocket address
config = ConfigurationManager.get().get("websocket")
url = WebsocketClient.build_url(config.get("host"),
                                config.get("port"),
                                config.get("route"),
                                config.get("ssl"))

# Send the provided message/data
ws = create_connection(url)
packet = Message(messageToSend, dataToSend).serialize()
ws.send(packet)
ws.close()
