# Copyright 2021 Mycroft AI Inc.
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
import logging


def create_echo_function(name):
    """Standard logging mechanism for Mycroft processes.

    This creats
    Arguments:
        name (str): Reference name of the process

    Returns:
        func: The echo function
    """
    log = logging.getLogger(name)
    def echo(message):
        try:
            msg = json.loads(message)
            msg_type = msg.get("type", "")
            # do not log tokens from registration messages
            if msg_type == "registration":
                msg["data"]["token"] = None
                message = json.dumps(msg)
        except Exception as e:
            log.info("Error: {}".format(repr(e)), exc_info=True)

        # Listen for messages and echo them for logging
        log.info("BUS: {}".format(message))
    return echo
