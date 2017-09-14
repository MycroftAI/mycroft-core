# Copyright 2017 Mycroft AI, Inc.
#
# This file is part of Mycroft Core.
#
# Mycroft Core is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Mycroft Core is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Mycroft Core.  If not, see <http://www.gnu.org/licenses/>.

from copy import copy

import requests
from requests import HTTPError

from mycroft.configuration import ConfigurationManager
from mycroft.identity import IdentityManager
from mycroft.version import VersionManager

__author__ = 'jdorleans'
_paired_cache = False


class Api(object):
    """ Generic object to wrap web APIs """

    def __init__(self, path):
        self.path = path
        config = ConfigurationManager.get()
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
        method = params.get("method", "GET")
        headers = self.build_headers(params)
        data = self.build_data(params)
        json = self.build_json(params)
        query = self.build_query(params)
        url = self.build_url(params)
        response = requests.request(method, url, headers=headers, params=query,
                                    data=data, json=json, timeout=(3.05, 15))
        return self.get_response(response)

    def get_response(self, response):
        data = self.get_data(response)
        if 200 <= response.status_code < 300:
            return data
        elif response.status_code == 401\
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
            for k, v in json.iteritems():
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
        return self.request({
            "method": "POST",
            "path": "/activate",
            "json": {"state": state,
                     "token": token,
                     "coreVersion": version.get("coreVersion"),
                     "enclosureVersion": version.get("enclosureVersion")}
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
        subscription_type = self.get_subscription().get('@type')
        return subscription_type != 'free'

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


class STTApi(Api):
    """ Web API wrapper for performing Speech to Text (STT) """

    def __init__(self):
        super(STTApi, self).__init__("stt")

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


def is_paired():
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
    except:
        return False
