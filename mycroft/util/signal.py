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
import time

import os
import os.path

import mycroft
from mycroft.util.file_utils import ensure_directory_exists, create_file, \
    get_temp_path


def get_ipc_directory(domain=None):
    """Get the directory used for Inter Process Communication

    Files in this folder can be accessed by different processes on the
    machine.  Useful for communication.  This is often a small RAM disk.

    Args:
        domain (str): The IPC domain.  Basically a subdirectory to prevent
            overlapping signal filenames.

    Returns:
        str: a path to the IPC directory
    """
    config = mycroft.configuration.Configuration.get()
    path = config.get("ipc_path")
    if not path:
        # If not defined, use /tmp/mycroft/ipc
        path = get_temp_path(mycroft.configuration.BASE_FOLDER, "ipc")
    return ensure_directory_exists(path, domain)


def create_signal(signal_name):
    """Create a named signal

    Args:
        signal_name (str): The signal's name.  Must only contain characters
            valid in filenames.
    """
    try:
        path = os.path.join(get_ipc_directory(), "signal", signal_name)
        create_file(path)
        return os.path.isfile(path)
    except IOError:
        return False


def check_for_signal(signal_name, sec_lifetime=0):
    """See if a named signal exists

    Args:
        signal_name (str): The signal's name.  Must only contain characters
            valid in filenames.
        sec_lifetime (int, optional): How many seconds the signal should
            remain valid.  If 0 or not specified, it is a single-use signal.
            If -1, it never expires.

    Returns:
        bool: True if the signal is defined, False otherwise
    """
    path = os.path.join(get_ipc_directory(), "signal", signal_name)
    if os.path.isfile(path):
        if sec_lifetime == 0:
            # consume this single-use signal
            _remove_signal(path)
        elif sec_lifetime == -1:
            return True
        elif int(os.path.getctime(path) + sec_lifetime) < int(time.time()):
            # remove once expired
            _remove_signal(path)
            return False
        return True

    # No such signal exists
    return False


def _remove_signal(signal_name):
    # this method is private because nothing should import it, if something
    # does that it wont work with regular mycroft-core, plus there is no
    # good reason to call this from elsewhere
    if os.path.isfile(signal_name):
        path = signal_name
    else:
        path = os.path.join(get_ipc_directory(), "signal", signal_name)
    # consume this signal
    try:
        os.remove(path)
    except:
        # some other process might have removed it meanwhile!
        if os.path.isfile(path):
            # what now? probably a file permission error,
            # this signal will keep triggering if file is not removed
            raise
