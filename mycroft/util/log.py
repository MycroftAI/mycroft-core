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
import logging

from os.path import isfile

SYSTEM_CONFIG = '/etc/mycroft/mycroft.conf'

__author__ = 'seanfitz'

log_level = "DEBUG"

if isfile(SYSTEM_CONFIG):
    with open(SYSTEM_CONFIG) as f:
        config = json.load(f)
        log_level = config.get("log_level", "DEBUG")

FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
logging.basicConfig(format=FORMAT, level=logging.getLevelName(log_level))
logger = logging.getLogger("MYCROFT")


def getLogger(name="MYCROFT"):
    """
    Get a python logger

    :param name: Module name for the logger

    :return: an instance of logging.Logger
    """
    return logging.getLogger(name)
