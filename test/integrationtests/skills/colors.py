# Copyright 2019 Mycroft AI Inc.
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
"""Color definitions for test output."""
import os


class Clr:
    PINK = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    DKGRAY = '\033[90m'
    # Classes
    USER_UTT = '\033[96m'  # cyan
    MYCROFT = '\033[33m'   # bright yellow
    HEADER = '\033[94m'    # blue
    WARNING = '\033[93m'   # yellow
    FAIL = '\033[91m'      # red
    RESET = '\033[0m'


class NoClr:
    PINK = ''
    BLUE = ''
    CYAN = ''
    GREEN = ''
    YELLOW = ''
    RED = ''
    DKGRAY = ''
    USER_UTT = ''
    MYCROFT = ''
    HEADER = ''
    WARNING = ''
    FAIL = ''
    RESET = ''


# MST as in Mycroft Skill Tester
if 'MST_NO_COLOR' not in os.environ:
    color = Clr
else:
    color = NoClr
