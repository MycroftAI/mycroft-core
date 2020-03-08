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
import tempfile
import time

import os
import os.path

import mycroft
from .file_utils import ensure_directory_exists, create_file


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
    dir = config.get("ipc_path")
    if not dir:
        # If not defined, use /tmp/mycroft/ipc
        dir = os.path.join(tempfile.gettempdir(), "mycroft", "ipc")
    return ensure_directory_exists(dir, domain)


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
            os.remove(path)
        elif sec_lifetime == -1:
            return True
        elif int(os.path.getctime(path) + sec_lifetime) < int(time.time()):
            # remove once expired
            os.remove(path)
            return False
        return True

    # No such signal exists
    return False
