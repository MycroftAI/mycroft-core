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
from unittest.mock import patch

from mycroft.messagebus.client import MessageBusClient

WS_CONF = {
    'websocket': {
        "host": "testhost",
        "port": 1337,
        "route": "/core",
        "ssl": False
    }
}


class TestMessageBusClient:
    def test_build_url(self):
        url = MessageBusClient.build_url('localhost', 1337, '/core', False)
        assert url == 'ws://localhost:1337/core'
        ssl_url = MessageBusClient.build_url('sslhost', 443, '/core', True)
        assert ssl_url == 'wss://sslhost:443/core'

    @patch('mycroft.configuration.Configuration.get', return_value=WS_CONF)
    def test_create_client(self, mock_conf):
        mc = MessageBusClient()
        assert mc.client.url == 'ws://testhost:1337/core'
