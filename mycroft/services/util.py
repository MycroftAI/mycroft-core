# Copyright 2020 Mycroft AI Inc.
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

from threading import Event
from mycroft.messagebus.client import MessageBusClient
from mycroft.configuration import Configuration
from mycroft.util import create_daemon, create_echo_function
from mycroft.util.log import LOG


def start_message_bus_client(service, bus=None, whitelist=None):
    """Start the bus client daemon and wait for connection.

    Arguments:
        service (str): name of the service starting the connection
        bus (MessageBusClient): an instance of the Mycroft MessageBusClient
    Returns:
        A connected instance of the MessageBusClient
    """
    # Create a client if one was not provided
    if bus is None:
        bus = MessageBusClient()
    Configuration.set_config_update_handlers(bus)
    bus_connected = Event()
    bus.on('message', create_echo_function(service, whitelist))
    # Set the bus connected event when connection is established
    bus.once('open', bus_connected.set)
    create_daemon(bus.run_forever)

    # Wait for connection
    bus_connected.wait()
    LOG.info('Connected to messagebus')

    return bus
