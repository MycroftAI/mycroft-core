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

import json
import requests
from requests import HTTPError, RequestException

from mycroft.configuration import Configuration
from mycroft.configuration.config import DEFAULT_CONFIG, SYSTEM_CONFIG, \
    USER_CONFIG
from mycroft.identity import IdentityManager
from mycroft.version import VersionManager
from mycroft.util import get_arch, connected, LOG
# python 2/3 compatibility
from future.utils import iteritems

_paired_cache = False


class BackendDown(RequestException):
    pass


class InternetDown(RequestException):
    pass


class Api(object):
    """ Generic object to wrap web APIs """
    params_to_etag = {}
    etag_to_response = {}

    def __init__(self, path):
        self.path = path

        # Load the config, skipping the REMOTE_CONFIG since we are
        # getting the info needed to get to it!
        config = Configuration.get([DEFAULT_CONFIG,
                                    SYSTEM_CONFIG,
                                    USER_CONFIG],
                                   cache=False)
        config_server = config.get("server")
        self.url = config_server.get("url")
        self.version = config_server.get("version")
        self.identity = IdentityManager.get()

    def request(self, params):
        self.check_token()
        self.build_path(params)
        self.old_params = copy(params)
        return self.send(params)

    def check_token(self):
        if self.identity.refresh and self.identity.is_expired():
            self.identity = IdentityManager.load()
            if self.identity.is_expired():
                self.refresh_token()

    def refresh_token(self):
        data = self.send({
            "path": "auth/token",
            "headers": {
                "Authorization": "Bearer " + self.identity.refresh
            }
        })
        IdentityManager.save(data)

    def send(self, params):
        """ Send request to mycroft backend.
        The method handles Etags and will return a cached response value
        if nothing has changed on the remote.

        Arguments:
            params (dict): request parameters

        Returns:
            Requests response object.
        """
        query_data = frozenset(params.get('query', {}).items())
        params_key = (params.get('path'), query_data)
        etag = self.params_to_etag.get(params_key)

        method = params.get("method", "GET")
        headers = self.build_headers(params)
        data = self.build_data(params)
        json_body = self.build_json(params)
        query = self.build_query(params)
        url = self.build_url(params)

        # For an introduction to the Etag feature check out:
        # https://en.wikipedia.org/wiki/HTTP_ETag
        if etag:
            headers['If-None-Match'] = etag

        response = requests.request(
            method, url, headers=headers, params=query,
            data=data, json=json_body, timeout=(3.05, 15)
        )
        if response.status_code == 304:
            LOG.debug('Etag matched. Nothing changed for: ' + params['path'])
            response = self.etag_to_response[etag]
        elif 'ETag' in response.headers:
            etag = response.headers['ETag'].strip('"')
            LOG.debug('Updating etag for: ' + params['path'])
            self.params_to_etag[params_key] = etag
            self.etag_to_response[etag] = response

        return self.get_response(response)

    def get_response(self, response):
        data = self.get_data(response)
        if 200 <= response.status_code < 300:
            return data
        elif response.status_code == 401 \
                and not response.url.endswith("auth/token"):
            self.refresh_token()
            return self.send(self.old_params)
        raise HTTPError(data, response=response)

    def get_data(self, response):
        try:
            return response.json()
        except:
            return response.text

    def build_headers(self, params):
        headers = params.get("headers", {})
        self.add_content_type(headers)
        self.add_authorization(headers)
        params["headers"] = headers
        return headers

    def add_content_type(self, headers):
        if not headers.__contains__("Content-Type"):
            headers["Content-Type"] = "application/json"

    def add_authorization(self, headers):
        if not headers.__contains__("Authorization"):
            headers["Authorization"] = "Bearer " + self.identity.access

    def build_data(self, params):
        return params.get("data")

    def build_json(self, params):
        json = params.get("json")
        if json and params["headers"]["Content-Type"] == "application/json":
            for k, v in iteritems(json):
                if v == "":
                    json[k] = None
            params["json"] = json
        return json

    def build_query(self, params):
        return params.get("query")

    def build_path(self, params):
        path = params.get("path", "")
        params["path"] = self.path + path
        return params["path"]

    def build_url(self, params):
        path = params.get("path", "")
        version = params.get("version", self.version)
        return self.url + "/" + version + "/" + path


class DeviceApi(Api):
    """ Web API wrapper for obtaining device-level information """

    def __init__(self):
        super(DeviceApi, self).__init__("device")

    def get_code(self, state):
        IdentityManager.update()
        return self.request({
            "path": "/code?state=" + state
        })

    def activate(self, state, token):
        version = VersionManager.get()
        platform = "unknown"
        platform_build = ""

        # load just the local configs to get platform info
        config = Configuration.get([SYSTEM_CONFIG,
                                    USER_CONFIG],
                                   cache=False)
        if "enclosure" in config:
            platform = config.get("enclosure").get("platform", "unknown")
            platform_build = config.get("enclosure").get("platform_build", "")

        return self.request({
            "method": "POST",
            "path": "/activate",
            "json": {"state": state,
                     "token": token,
                     "coreVersion": version.get("coreVersion"),
                     "platform": platform,
                     "platform_build": platform_build,
                     "enclosureVersion": version.get("enclosureVersion")}
        })

    def update_version(self):
        version = VersionManager.get()
        platform = "unknown"
        platform_build = ""

        # load just the local configs to get platform info
        config = Configuration.get([SYSTEM_CONFIG,
                                    USER_CONFIG],
                                   cache=False)
        if "enclosure" in config:
            platform = config.get("enclosure").get("platform", "unknown")
            platform_build = config.get("enclosure").get("platform_build", "")

        return self.request({
            "method": "PATCH",
            "path": "/" + self.identity.uuid,
            "json": {"coreVersion": version.get("coreVersion"),
                     "platform": platform,
                     "platform_build": platform_build,
                     "enclosureVersion": version.get("enclosureVersion")}
        })

    def send_email(self, title, body, sender):
        return self.request({
            "method": "PUT",
            "path": "/" + self.identity.uuid + "/message",
            "json": {"title": title, "body": body, "sender": sender}
        })

    def report_metric(self, name, data):
        return self.request({
            "method": "POST",
            "path": "/" + self.identity.uuid + "/metric/" + name,
            "json": data
        })

    def get(self):
        """ Retrieve all device information from the web backend """
        return self.request({
            "path": "/" + self.identity.uuid
        })

    def get_settings(self):
        """ Retrieve device settings information from the web backend

        Returns:
            str: JSON string with user configuration information.
        """
        return self.request({
            "path": "/" + self.identity.uuid + "/setting"
        })

    def get_location(self):
        """ Retrieve device location information from the web backend

        Returns:
            str: JSON string with user location.
        """
        return self.request({
            "path": "/" + self.identity.uuid + "/location"
        })

    def get_subscription(self):
        """
            Get information about type of subscrition this unit is connected
            to.

            Returns: dictionary with subscription information
        """
        return self.request({
            'path': '/' + self.identity.uuid + '/subscription'})

    @property
    def is_subscriber(self):
        """
            status of subscription. True if device is connected to a paying
            subscriber.
        """
        try:
            return self.get_subscription().get('@type') != 'free'
        except:
            # If can't retrieve, assume not paired and not a subscriber yet
            return False

    def get_subscriber_voice_url(self, voice=None):
        self.check_token()
        archs = {'x86_64': 'x86_64', 'armv7l': 'arm', 'aarch64': 'arm'}
        arch = archs.get(get_arch())
        if arch:
            path = '/' + self.identity.uuid + '/voice?arch=' + arch
            return self.request({'path': path})['link']

    def find(self):
        """ Deprecated, see get_location() """
        # TODO: Eliminate ASAP, for backwards compatibility only
        return self.get()

    def find_setting(self):
        """ Deprecated, see get_settings() """
        # TODO: Eliminate ASAP, for backwards compatibility only
        return self.get_settings()

    def find_location(self):
        """ Deprecated, see get_location() """
        # TODO: Eliminate ASAP, for backwards compatibility only
        return self.get_location()

    def get_oauth_token(self, dev_cred):
        """
            Get Oauth token for dev_credential dev_cred.

            Argument:
                dev_cred:   development credentials identifier

            Returns:
                json string containing token and additional information
        """
        return self.request({
            "method": "GET",
            "path": "/" + self.identity.uuid + "/token/" + str(dev_cred)
        })


class STTApi(Api):
    """ Web API wrapper for performing Speech to Text (STT) """

    def __init__(self, path):
        super(STTApi, self).__init__(path)

    def stt(self, audio, language, limit):
        """ Web API wrapper for performing Speech to Text (STT)

        Args:
            audio (bytes): The recorded audio, as in a FLAC file
            language (str): A BCP-47 language code, e.g. "en-US"
            limit (int): Maximum minutes to transcribe(?)

        Returns:
            str: JSON structure with transcription results
        """

        return self.request({
            "method": "POST",
            "headers": {"Content-Type": "audio/x-flac"},
            "query": {"lang": language, "limit": limit},
            "data": audio
        })


def has_been_paired():
    """ Determine if this device has ever been paired with a web backend

    Returns:
        bool: True if ever paired with backend (not factory reset)
    """
    # This forces a load from the identity file in case the pairing state
    # has recently changed
    id = IdentityManager.load()
    return id.uuid is not None and id.uuid != ""


def is_paired(ignore_errors=True):
    """ Determine if this device is actively paired with a web backend

    Determines if the installation of Mycroft has been paired by the user
    with the backend system, and if that pairing is still active.

    Returns:
        bool: True if paired with backend
    """
    global _paired_cache
    if _paired_cache:
        # NOTE: This assumes once paired, the unit remains paired.  So
        # un-pairing must restart the system (or clear this value).
        # The Mark 1 does perform a restart on RESET.
        return True

    try:
        api = DeviceApi()
        device = api.get()
        _paired_cache = api.identity.uuid is not None and \
            api.identity.uuid != ""
        return _paired_cache
    except HTTPError as e:
        if e.response.status_code == 401:
            return False
    except Exception as e:
        LOG.warning('Could not get device infO: ' + repr(e))
    if ignore_errors:
        return False
    if connected():
        raise BackendDown
    raise InternetDown
