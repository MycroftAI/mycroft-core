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

from mycroft.messagebus.send_func import send


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


if __name__ == '__main__':
    try:
        main()
    except IOError:
        print('Could not connect to websocket, no message sent')
