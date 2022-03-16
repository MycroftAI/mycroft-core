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

from genericpath import exists, isfile
from os.path import join, expanduser

from mycroft.configuration import Configuration
from mycroft.util.log import LOG

# The following lines are replaced during the release process.
# START_VERSION_BLOCK
CORE_VERSION_MAJOR = 21
CORE_VERSION_MINOR = 2
CORE_VERSION_BUILD = 1

OVOS_VERSION_MAJOR = 0
OVOS_VERSION_MINOR = 0
OVOS_VERSION_BUILD = 2
OVOS_VERSION_ALPHA = 19


# END_VERSION_BLOCK


CORE_VERSION_TUPLE = (CORE_VERSION_MAJOR,
                      CORE_VERSION_MINOR,
                      CORE_VERSION_BUILD)
CORE_VERSION_STR = '.'.join(map(str, CORE_VERSION_TUPLE))

OVOS_VERSION_TUPLE = (OVOS_VERSION_MAJOR,
                      OVOS_VERSION_MINOR,
                      OVOS_VERSION_BUILD)
OVOS_VERSION_STR = '.'.join(map(str, OVOS_VERSION_TUPLE))


class VersionManager:
    @staticmethod
    def get():
        return {"coreVersion": CORE_VERSION_STR,
                "OpenVoiceOSVersion": OVOS_VERSION_STR,
                "enclosureVersion": None}


def check_version(version_string):
    """
        Check if current version is equal or higher than the
        version string provided to the function

        Args:
            version_string (string): version string ('Major.Minor.Build')
    """
    version_tuple = tuple(map(int, version_string.split('.')))
    return CORE_VERSION_TUPLE >= version_tuple
