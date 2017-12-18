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
import shutil
import subprocess

import os
from setuptools import find_packages

from mycroft.util.log import LOG


BASEDIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))


def place_manifest(manifest_file):
    shutil.copy(manifest_file, "MANIFEST.in")


def get_version():
    version = None
    try:
        from mycroft.version import CORE_VERSION_STR
        version = CORE_VERSION_STR
    except Exception as e:
        try:
            version = "dev-" + subprocess.check_output(
                ["git", "rev-parse", "--short", "HEAD"]).strip()
        except subprocess.CalledProcessError as e2:
            version = "development"
            LOG.debug(e)
            LOG.exception(e2)

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
