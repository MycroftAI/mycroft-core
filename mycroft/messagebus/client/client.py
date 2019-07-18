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

# WebSocketClient has been deprecated in favor of the new MessageBusClient
# This is a backport for any skills using the message bus client.

# TODO: remove as part of 19.08
from mycroft.util.log import LOG
from .client import MessageBusClient


class WebsocketClient(MessageBusClient):
    def __init__(self):
        super().__init__()
        LOG.warning(
            "WebsocketClient is deprecated, use MessageBusClient instead"
        )
