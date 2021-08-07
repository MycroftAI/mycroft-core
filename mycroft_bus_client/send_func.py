# Copyright 2019 Mycroft AI Inc.
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
from websocket import create_connection

from .client import MessageBusClient
from .message import Message


def send(message_to_send, data_to_send=None, config=None):
    """Send a single message over the websocket.

    Args:
        message_to_send (str): Message to send
        data_to_send (dict): data structure to go along with the
            message, defaults to empty dict.
    """
    data_to_send = data_to_send or {}

    url = MessageBusClient.build_url(config.get("host"),
                                     config.get("port"),
                                     config.get("route"),
                                     config.get("ssl"))

    # Send the provided message/data
    ws = create_connection(url)
    packet = Message(message_to_send, data_to_send).serialize()
    ws.send(packet)
    ws.close()
