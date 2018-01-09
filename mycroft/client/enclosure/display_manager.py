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
import json
from threading import Thread, Timer

import os

from mycroft.messagebus.client.ws import WebsocketClient
from mycroft.util import get_ipc_directory
from mycroft.util.log import LOG


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
    LOG.info("Initiating display manager websocket")

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
