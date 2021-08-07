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
import json

from .client import MessageBusClient

def client_from_config(subconf='core', file_path='/etc/mycroft/bus.conf'):
    """Load messagebus configuration from file.

    The config is a basic json file with a number of "sub configurations"

    Ex:
    {
      "core": {
        "route": "/core",
        "port": "8181"
      }
      "gui": {
        "route": "/gui",
        "port": "8811"
      }
    }

    Arguments:
        subconf:    configuration to choose from the file, defaults to "core"
                    if omitted.
        file_path:  path to the config file, defaults to /etc/mycroft/bus.conf
                    if omitted.
    Returns:
        MessageBusClient instance based on the selected config.
    """
    with open(file_path) as f:
        conf = json.load(f)

    return MessageBusClient(**conf[subconf])
