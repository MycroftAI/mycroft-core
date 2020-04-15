# Copyright 2020 Mycroft AI Inc.
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
import os
import subprocess
import sys
from .test_setup import main as test_setup
from .test_setup import create_argument_parser
"""Voigt Kampff Test Module

A single interface for the Voice Kampff integration test module.

Full documentation can be found at https://mycroft.ai/docs
"""


def main(cmdline_args):
    parser = create_argument_parser()
    setup_args, behave_args = parser.parse_known_args(cmdline_args)
    test_setup(setup_args)
    os.chdir(os.path.dirname(__file__))
    subprocess.call(['./run_test_suite.sh', *behave_args])


if __name__ == '__main__':
    main(sys.argv[1:])
