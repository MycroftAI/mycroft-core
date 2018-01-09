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
CORE_VERSION_MAJOR = 0
CORE_VERSION_MINOR = 9
CORE_VERSION_BUILD = 13
# END_VERSION_BLOCK

CORE_VERSION_STR = (str(CORE_VERSION_MAJOR) + "." +
                    str(CORE_VERSION_MINOR) + "." +
                    str(CORE_VERSION_BUILD))


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
    major, minor, build = version_string.split('.')
    major = int(major)
    minor = int(minor)
    build = int(build)

    if CORE_VERSION_MAJOR > major:
        return True
    elif CORE_VERSION_MAJOR == major and CORE_VERSION_MINOR > minor:
        return True
    elif major == CORE_VERSION_MAJOR and minor == CORE_VERSION_MINOR and \
            CORE_VERSION_BUILD >= build:
        return True
    else:
        return False
