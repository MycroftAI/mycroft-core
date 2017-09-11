
# Copyright 2017 Mycroft AI, Inc.
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
from threading import Thread, Timer
from mycroft.messagebus.client.ws import WebsocketClient
from mycroft.configuration import ConfigurationManager
from mycroft.util import get_ipc_directory
import json
import os
from logging import getLogger

__author__ = 'connorpenrod', 'michaelnguyen'


LOG = getLogger("Display Manager (mycroft.client.enclosure)")


def _write_data(dictionary):
    """Writes the parama as JSON to the
        IPC dir (/tmp/mycroft/ipc/managers)
        args:
            dict: dictionary
    """

    managerIPCDir = os.path.join(get_ipc_directory(), "managers")
    # change read/write permissions based on if file exists or not
    path = os.path.join(managerIPCDir, "disp_info")
    permission = "r+" if os.path.isfile(path) else "w+"

    if permission == "w+" and os.path.isdir(managerIPCDir) is False:
        os.makedirs(managerIPCDir)
        os.chmod(managerIPCDir, 0777)

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

        os.chmod(path, 0777)

    except Exception as e:
        LOG.error(e)
        LOG.error("Error found in display manager file, deleting...")
        os.remove(path)
        _write_data(dictionary)


def _read_data():
    """ Reads the file in (/tmp/mycroft/ipc/managers/disp_info)
        and returns the the data as python dict
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


def set_active(skill_name):
    """ Sets skill name as active in the display Manager
        args:
            string: skill_name
    """
    _write_data({"active_skill": skill_name})
    LOG.debug("Setting active skill to " + skill_name)


def get_active():
    """ Get active skill in the display manager
    """
    data = _read_data()
    active_skill = ""

    if "active_skill" in data:
        active_skill = data["active_skill"]

    return active_skill


def remove_active():
    """ Remove the active skill in the skill manager
    """
    LOG.debug("Removing active skill...")
    _write_data({"active_skill": ""})


def initiate_display_manager_ws():
    """ Initiates the web sockets on the display_manager
    """
    LOG.info("Initiating dispaly manager websocket")

    # Should remove needs to be an object so it can be referenced in functions
    # [https://stackoverflow.com/questions/986006/how-do-i-pass-a-variable-by-reference]
    should_remove = [True]

    def check_flag(flag):
        if flag[0] is True:
            remove_active()

    def set_delay(event=None):
        should_remove[0] = True
        Timer(2, check_flag, [should_remove]).start()

    def set_remove_flag(event=None):
        should_remove[0] = False

    def connect():
        ws.run_forever()

    def remove_wake_word():
        data = _read_data()
        if "active_skill" in data and data["active_skill"] == "wakeword":
            remove_active()

    def set_wakeword_skill(event=None):
        set_active("wakeword")
        Timer(10, remove_wake_word).start()

    ws = WebsocketClient()
    ws.on('recognizer_loop:audio_output_end', set_delay)
    ws.on('recognizer_loop:audio_output_start', set_remove_flag)
    ws.on('recognizer_loop:record_begin', set_wakeword_skill)

    event_thread = Thread(target=connect)
    event_thread.setDaemon(True)
    event_thread.start()
