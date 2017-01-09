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


import os
import subprocess
from setuptools import find_packages
import shutil
from mycroft.util.log import getLogger


__author__ = 'seanfitz'

BASEDIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
logger = getLogger(__name__)


def place_manifest(manifest_file):
    shutil.copy(manifest_file, "MANIFEST.in")


def get_version():
    version = None
    try:
        import mycroft.__version__
        version = mycroft.__version__.version
    except Exception as e:
        try:
            version = "dev-" + subprocess.check_output(
                ["git", "rev-parse", "--short", "HEAD"]).strip()
        except subprocess.CalledProcessError as e2:
            version = "development"
            logger.debug(e)
            logger.exception(e2)

    return version


def required(requirements_file):
    with open(os.path.join(BASEDIR, requirements_file), 'r') as f:
        requirements = f.read().splitlines()
        return [pkg for pkg in requirements if not pkg.startswith("--")]


def find_all_packages(where):
    packages = find_packages(where=where, exclude=["*test*"])
    return [
        os.path.join(where, pkg.replace(".", os.sep))
        for pkg in packages] + [where]
