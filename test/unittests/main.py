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
import sys
from unittest import TestLoader

from os.path import dirname
from xmlrunner import XMLTestRunner

from mycroft.configuration import ConfigurationManager


if __name__ == "__main__":
    fail_on_error = "--fail-on-error" in sys.argv
    ConfigurationManager.load_local(['mycroft.conf'], keep_user_config=False)

    tests = TestLoader().discover(dirname(__file__), "*.py")
    result = XMLTestRunner("./build/report/tests").run(tests)

    if fail_on_error and len(result.failures + result.errors) > 0:
        sys.exit(1)
