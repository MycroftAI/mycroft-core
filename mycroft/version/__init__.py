# Copyright 2016 Mycroft AI, Inc.
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

import json
from genericpath import exists, isfile

from mycroft.util.log import getLogger

__author__ = 'augustnmonteiro'

# The following lines are replaced during the release process.
# START_VERSION_BLOCK
CORE_VERSION_MAJOR = 0
CORE_VERSION_MINOR = 8
CORE_VERSION_BUILD = 20
# END_VERSION_BLOCK

CORE_VERSION_STR = (str(CORE_VERSION_MAJOR) + "." +
                    str(CORE_VERSION_MINOR) + "." +
                    str(CORE_VERSION_BUILD))
LOG = getLogger(__name__)


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
