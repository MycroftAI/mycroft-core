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
from copy import copy
from http import HTTPStatus
from unittest import TestCase
from unittest.mock import MagicMock, patch

from requests import HTTPError

from mycroft.api import (
    Api, DeviceApi, STTApi, has_been_paired, is_paired, BackendDown
)
from ..mocks import base_config

API_DOMAIN = 'https://api-test.mycroft.ai'


def mock_identity(paired=True):
    identity_mock = MagicMock()
    identity_mock.is_expired.return_value = False
    if paired:
        identity_mock.uuid = "1234"
    else:
        identity_mock.uuid = ""

    return identity_mock


def mock_http_response(status, json=None, url=''):
    response = MagicMock()
    response.status_code = status
    response.json.return_value = json or {}
    response.url = url

    return response


class ApiTestBase(TestCase):
    def setUp(self):
        self._patch_config()
        self._patch_requests()
        self._patch_identity()
        super().setUp()

    def _patch_config(self):
        config = base_config()
        server_config = dict(
            url=API_DOMAIN,
            version='v1',
            update=True,
            metrics=False
        )
        config.update(data_dir='/opt/mycroft', server=server_config)
        patcher = patch(
            'mycroft.configuration.Configuration.get', return_value=config
        )
        self.config_mock = patcher.start()
        self.addCleanup(patcher.stop)

    def _patch_requests(self):
        patcher = patch('mycroft.api.requests.request')
        self.http_request_mock = patcher.start()
        self.http_response_ok = mock_http_response(HTTPStatus.OK)
        self.http_request_mock.return_value = self.http_response_ok
        self.addCleanup(patcher.stop)
        patcher = patch('mycroft.api.requests.post')
        self.mock_post = patcher.start()
        self.addCleanup(patcher.stop)

    def _patch_identity(self):
        patcher = patch('mycroft.api.IdentityManager')
        self.identity_mock = patcher.start()
        self.identity_mock.get = MagicMock(return_value=mock_identity())
        self.addCleanup(patcher.stop)

    def _check_api_request(self, url, method):
        request_url = self.http_request_mock.call_args[0][1]
        self.assertEqual(request_url, API_DOMAIN + url)
        request_method = self.http_request_mock.call_args[0][0]
        self.assertEqual(request_method, method)


class TestApi(ApiTestBase):
    def test_init(self):
        self.identity_mock.get = MagicMock(return_value=mock_identity())
        api = Api('test-path')
        self.assertEqual(api.url, API_DOMAIN)
        self.assertEqual(api.version, 'v1')
        self.assertEqual(api.identity.uuid, '1234')

    def test_send(self):
        mock_response_301 = mock_http_response(HTTPStatus.MOVED_PERMANENTLY)
        mock_response_401 = mock_http_response(
            HTTPStatus.UNAUTHORIZED, url='auth/token'
        )
        mock_response_refresh = mock_http_response(
            HTTPStatus.UNAUTHORIZED, url=''
        )

        self.http_request_mock.return_value = self.http_response_ok
        api = Api('test-path')
        req = {'path': 'something', 'headers': {}}

        # Check successful
        self.assertEqual(api.send(req), self.http_response_ok.json())

        # check that a 300+ status code generates Exception
        self.http_request_mock.return_value = mock_response_301
        with self.assertRaises(HTTPError):
            api.send(req)

        # Check 401
        self.http_request_mock.return_value = mock_response_401
        req = {'path': '', 'headers': {}}
        with self.assertRaises(HTTPError):
            api.send(req)

        # Check refresh token
        api.identity.is_expired = MagicMock(return_value=True)
        api.old_params = copy(req)
        self.http_request_mock.side_effect = [
            mock_response_refresh, self.http_response_ok, self.http_response_ok
        ]
        req = {'path': 'something', 'headers': {}}
        api.send(req)
        self.assertTrue(self.identity_mock.save.called)


class TestDeviceApi(ApiTestBase):
    def test_init(self):
        device = DeviceApi()
        self.assertEqual(device.identity.uuid, '1234')
        self.assertEqual(device.path, 'device')

    def test_device_activate(self):
        device = DeviceApi()
        device.activate('state', 'token')
        json = self.http_request_mock.call_args[1]['json']
        self.assertEqual(json['state'], 'state')
        self.assertEqual(json['token'], 'token')

    def test_device_get(self):
        device = DeviceApi()
        device.get()
        self._check_api_request('/v1/device/1234', 'GET')

    def test_device_get_code(self):
        self.http_request_mock.return_value = mock_http_response(200, '123ABC')
        device = DeviceApi()
        pairing_code = device.get_code('state')
        self.assertEqual(pairing_code, '123ABC')
        self._check_api_request('/v1/device/code?state=state', 'GET')

    def test_device_get_settings(self):
        device = DeviceApi()
        device.get_settings()
        self._check_api_request('/v1/device/1234/setting', 'GET')

    def test_device_report_metric(self):
        device = DeviceApi()
        device.report_metric('my_metric', {'data': 'my_data'})
        params = self.http_request_mock.call_args[1]

        content_type = params['headers']['Content-Type']
        correct_json = {'data': 'my_data'}
        self.assertEqual(content_type, 'application/json')
        self.assertEqual(params['json'], correct_json)
        self._check_api_request('/v1/device/1234/metric/my_metric', 'POST')

    def test_device_send_email(self):
        device = DeviceApi()
        device.send_email('title', 'body', 'sender')
        params = self.http_request_mock.call_args[1]

        content_type = params['headers']['Content-Type']
        correct_json = {'body': 'body', 'sender': 'sender', 'title': 'title'}
        self.assertEqual(content_type, 'application/json')
        self.assertEqual(params['json'], correct_json)
        self._check_api_request('/v1/device/1234/message', 'PUT')

    def test_device_get_oauth_token(self):
        device = DeviceApi()
        device.get_oauth_token(1)
        self._check_api_request('/v1/device/1234/token/1', 'GET')

    def test_device_get_location(self):
        device = DeviceApi()
        device.get_location()
        self._check_api_request('/v1/device/1234/location', 'GET')

    def test_device_get_subscription(self):
        device = DeviceApi()
        device.get_subscription()
        self._check_api_request('/v1/device/1234/subscription', 'GET')

        request_json = {'@type': 'free'}
        self.http_request_mock.return_value = mock_http_response(200, request_json)
        self.assertFalse(device.is_subscriber)

        request_json = {'@type': 'monthly'}
        self.http_request_mock.return_value = mock_http_response(200, request_json)
        self.assertTrue(device.is_subscriber)

        request_json = {'@type': 'yearly'}
        self.http_request_mock.return_value = mock_http_response(200, request_json)
        self.assertTrue(device.is_subscriber)

    def test_device_upload_skills_data(self):
        device = DeviceApi()
        device.upload_skills_data({})
        data = self.http_request_mock.call_args[1]['json']

        # Check that the correct url is called
        self._check_api_request('/v1/device/1234/skillJson', 'PUT')

        # Check that the correct data is sent as json
        self.assertTrue('blacklist' in data)
        self.assertTrue('skills' in data)

        with self.assertRaises(ValueError):
            device.upload_skills_data('This isn\'t right at all')

    def test_has_been_paired(self):
        identity_load_mock = MagicMock()
        self.identity_mock.load = MagicMock(return_value=identity_load_mock)
        # Test None
        identity_load_mock.uuid = None
        self.assertFalse(has_been_paired())
        # Test empty string
        identity_load_mock.uuid = ""
        self.assertFalse(has_been_paired())
        # Test actual id number
        identity_load_mock.uuid = "1234"
        self.assertTrue(has_been_paired())

    def test_upload_meta(self):
        device = DeviceApi()

        settings_section = dict(
            name='Settings',
            fields=[dict(name='Set me', type='number', value=4)]
        )
        settings_meta = dict(
            name='TestMeta',
            skill_gid='test_skill|19.02',
            skillMetadata=dict(sections=[settings_section])
        )
        device.upload_skill_metadata(settings_meta)
        params = self.http_request_mock.call_args[1]

        content_type = params['headers']['Content-Type']
        self.assertEqual(content_type, 'application/json')
        self.assertEqual(params['json'], settings_meta)
        self._check_api_request('/v1/device/1234/settingsMeta', 'PUT')

    def test_get_skill_settings(self):
        device = DeviceApi()
        device.get_skill_settings()

        self._check_api_request('/v1/device/1234/skill/settings', 'GET')


class TestSttApi(ApiTestBase):
    def test_stt(self):
        stt = STTApi('stt')
        self.assertEqual(stt.path, 'stt')

    def test_stt_stt(self):
        stt = STTApi('stt')
        stt.stt('La la la', 'en-US', 1)
        self._check_api_request('/v1/stt', 'POST')
        data = self.http_request_mock.call_args[1].get('data')
        self.assertEqual(data, 'La la la')
        params = self.http_request_mock.call_args[1].get('params')
        self.assertEqual(params['lang'], 'en-US')


@patch('mycroft.api._paired_cache', False)
class TestIsPaired(ApiTestBase):
    def test_is_paired_true(self):
        num_calls = self.identity_mock.get.num_calls
        self.assertTrue(is_paired())
        self.assertEqual(num_calls, self.identity_mock.get.num_calls)
        self._check_api_request('/v1/device/1234', 'GET')

    def test_is_paired_false_local(self):
        self.identity_mock.get.return_value = mock_identity(paired=False)
        self.assertFalse(is_paired())
        self.identity_mock.uuid = None
        self.assertFalse(is_paired())

    def test_is_paired_false_remote(self):
        self.http_request_mock.return_value = mock_http_response(
            HTTPStatus.UNAUTHORIZED
        )
        self.assertFalse(is_paired())

    def test_is_paired_error_remote(self):
        self.http_request_mock.return_value = mock_http_response(
            HTTPStatus.INTERNAL_SERVER_ERROR
        )
        self.assertFalse(is_paired())

        with self.assertRaises(BackendDown):
            is_paired(ignore_errors=False)
