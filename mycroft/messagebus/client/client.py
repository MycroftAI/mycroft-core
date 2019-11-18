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
from mycroft.messagebus.load_config import load_message_bus_config
from mycroft_bus_client import MessageBusClient as _MessageBusClient


class MessageBusClient(_MessageBusClient):
    def __init__(self, host=None, port=None, route=None, ssl=None):
        config_overrides = dict(host=host, port=port, route=route, ssl=ssl)
        config = load_message_bus_config(**config_overrides)
        super().__init__(config.host, config.port, config.route, config.ssl)
