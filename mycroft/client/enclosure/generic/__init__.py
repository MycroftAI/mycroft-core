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
from threading import Thread, Timer

import mycroft.dialog
from mycroft.client.enclosure.base import Enclosure
from mycroft.api import has_been_paired
from mycroft.audio import wait_while_speaking
from mycroft.enclosure.display_manager import \
    init_display_manager_bus_connection
from mycroft.messagebus.message import Message
from mycroft.util import connected
from mycroft.util.log import LOG


class EnclosureGeneric(Enclosure):
    """
    Serves as a communication interface between a simple text frontend and
    Mycroft Core.  This is used for Picroft or other headless systems,
    and/or for users of the CLI.
    """
    def __init__(self):
        super().__init__()
        # initiates the web sockets on display manager
        # NOTE: this is a temporary place to connect the display manager
        init_display_manager_bus_connection()
