#!/bin/bash
#
# Copyright 2018 Mycroft AI Inc.
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


# This script places the user in the mycroft-core virtual environment,
# necessary to run unit tests or to interact directly with mycroft-core
# via an interactive Python shell.

if [ "$0" = "$BASH_SOURCE" ] ; then
    # Prevent running in script then exiting immediately
    echo "ERROR: Invoke with 'source venv-activate.sh' or '. venv-activate.sh'"
else
    echo "Entering mycroft-core virtual environment.  Run 'deactivate' to exit"
    source .venv/bin/activate
fi
