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


"""
NOTE: this is dead code! do not use!

This file is only present to ensure backwards compatibility
in case someone is importing from here

This is only meant for 3rd party code expecting ovos-core
to be a drop in replacement for mycroft-core

TODO: consider importing from PHAL
"""

""" DisplayManager

This module provides basic "state" for the visual representation associated
with this Mycroft instance.  The current states are:
   ActiveSkill - The skill that last interacted with the display via the
                 Enclosure API.

Currently, a wakeword sets the ActiveSkill to "wakeword", which will auto
clear after 10 seconds.

A skill is set to Active when it matches an intent, outputs audio, or
changes the display via the EnclosureAPI()

A skill is automatically cleared from Active two seconds after audio
output is spoken, or 2 seconds after resetting the display.

So it is common to have '' as the active skill.
"""

import json
from threading import Thread, Timer

import os

from mycroft.messagebus.client import MessageBusClient
from mycroft.util import get_ipc_directory
from mycroft.util.log import LOG


def _write_data(dictionary):
    """ Writes the dictionary of state data to the IPC directory.

    Args:
        dictionary (dict): information to place in the 'disp_info' file
    """

    managerIPCDir = os.path.join(get_ipc_directory(), "managers")
    # change read/write permissions based on if file exists or not
    path = os.path.join(managerIPCDir, "disp_info")
    permission = "r+" if os.path.isfile(path) else "w+"

    if permission == "w+" and os.path.isdir(managerIPCDir) is False:
        os.makedirs(managerIPCDir)
        os.chmod(managerIPCDir, 0o777)

    try:
        with open(path, permission) as dispFile:

            # check if file is empty
            if os.stat(str(dispFile.name)).st_size != 0:
                data = json.load(dispFile)

            else:
                data = {}
                LOG.info("Display Manager is creating " + dispFile.name)

            for key in dictionary:
                data[key] = dictionary[key]

            dispFile.seek(0)
            dispFile.write(json.dumps(data))
            dispFile.truncate()

        os.chmod(path, 0o777)

    except Exception as e:
        LOG.error(e)
        LOG.error("Error found in display manager file, deleting...")
        os.remove(path)
        _write_data(dictionary)


def _read_data():
    """ Writes the dictionary of state data from the IPC directory.
    Returns:
        dict: loaded state information
    """
    managerIPCDir = os.path.join(get_ipc_directory(), "managers")

    path = os.path.join(managerIPCDir, "disp_info")
    permission = "r" if os.path.isfile(path) else "w+"

    if permission == "w+" and os.path.isdir(managerIPCDir) is False:
        os.makedirs(managerIPCDir)

    data = {}
    try:
        with open(path, permission) as dispFile:

            if os.stat(str(dispFile.name)).st_size != 0:
                data = json.load(dispFile)

    except Exception as e:
        LOG.error(e)
        os.remove(path)
        _read_data()

    return data


class DisplayManager:
    """ The Display manager handles the basic state of the display,
    be it a mark-1 or a mark-2 or even a future Mark-3.
    """

    def __init__(self, name=None):
        self.name = name or ""

    def set_active(self, skill_name=None):
        """ Sets skill name as active in the display Manager
        Args:
            string: skill_name
        """
        name = skill_name if skill_name is not None else self.name
        _write_data({"active_skill": name})

    def get_active(self):
        """ Get the currenlty active skill from the display manager
        Returns:
            string: The active skill's name
        """
        data = _read_data()
        active_skill = ""

        if "active_skill" in data:
            active_skill = data["active_skill"]

        return active_skill

    def remove_active(self):
        """ Clears the active skill """
        LOG.debug("Removing active skill...")
        _write_data({"active_skill": ""})


def init_display_manager_bus_connection():
    """ Connects the display manager to the messagebus """
    LOG.info("Connecting display manager to messagebus")

    # Should remove needs to be an object so it can be referenced in functions
    # [https://stackoverflow.com/questions/986006/how-do-i-pass-a-variable-by-reference]
    display_manager = DisplayManager()
    should_remove = [True]

    def check_flag(flag):
        if flag[0] is True:
            display_manager.remove_active()

    def set_delay(event=None):
        should_remove[0] = True
        Timer(2, check_flag, [should_remove]).start()

    def set_remove_flag(event=None):
        should_remove[0] = False

    def connect():
        bus.run_forever()

    def remove_wake_word():
        data = _read_data()
        if "active_skill" in data and data["active_skill"] == "wakeword":
            display_manager.remove_active()

    def set_wakeword_skill(event=None):
        display_manager.set_active("wakeword")
        Timer(10, remove_wake_word).start()

    bus = MessageBusClient()
    bus.on('recognizer_loop:audio_output_end', set_delay)
    bus.on('recognizer_loop:audio_output_start', set_remove_flag)
    bus.on('recognizer_loop:record_begin', set_wakeword_skill)

    event_thread = Thread(target=connect)
    event_thread.setDaemon(True)
    event_thread.start()
