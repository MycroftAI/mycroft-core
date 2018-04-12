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

from mycroft.util.log import LOG


# The following lines are replaced during the release process.
# START_VERSION_BLOCK
CORE_VERSION_MAJOR = 18
CORE_VERSION_MINOR = 2
CORE_VERSION_BUILD = 4
# END_VERSION_BLOCK

CORE_VERSION_TUPLE = (CORE_VERSION_MAJOR,
                      CORE_VERSION_MINOR,
                      CORE_VERSION_BUILD)
CORE_VERSION_STR = '.'.join(map(str, CORE_VERSION_TUPLE))


class VersionManager(object):
    __location = "/opt/mycroft/version.json"

    @staticmethod
    def get():
        if (exists(VersionManager.__location) and
                isfile(VersionManager.__location)):
            try:
                with open(VersionManager.__location) as f:
                    return json.load(f)
            except:
                LOG.error("Failed to load version from '%s'"
                          % VersionManager.__location)
        return {"coreVersion": None, "enclosureVersion": None}


def check_version(version_string):
    """
        Check if current version is equal or higher than the
        version string provided to the function

        Args:
            version_string (string): version string ('Major.Minor.Build')
    """
    version_tuple = tuple(map(int, version_string.split('.')))
    return CORE_VERSION_TUPLE >= version_tuple
