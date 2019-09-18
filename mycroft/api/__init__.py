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
import os
import time
from copy import copy

import requests
from requests import HTTPError, RequestException

from mycroft.configuration import Configuration
from mycroft.configuration.config import DEFAULT_CONFIG, SYSTEM_CONFIG, \
    USER_CONFIG
from mycroft.identity import IdentityManager, identity_lock
from mycroft.version import VersionManager
from mycroft.util import get_arch, connected, LOG


_paired_cache = False


class BackendDown(RequestException):
    pass


class InternetDown(RequestException):
    pass


UUID = '{MYCROFT_UUID}'


class Api:
    """ Generic class to wrap web APIs """
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
        if 'path' in params:
            params['path'] = params['path'].replace(UUID, self.identity.uuid)
        self.build_path(params)
        self.old_params = copy(params)
        return self.send(params)

    def check_token(self):
        # If the identity hasn't been loaded, load it
        if not self.identity.has_refresh():
            self.identity = IdentityManager.load()
        # If refresh is needed perform a refresh
        if self.identity.refresh and self.identity.is_expired():
            self.identity = IdentityManager.load()
            # if no one else has updated the token refresh it
            if self.identity.is_expired():
                self.refresh_token()

    def refresh_token(self):
        LOG.debug('Refreshing token')
        if identity_lock.acquire(blocking=False):
            try:
                data = self.send({
                    "path": "auth/token",
                    "headers": {
                        "Authorization": "Bearer " + self.identity.refresh,
                        "Device": self.identity.uuid
                    }
                })
                IdentityManager.save(data, lock=False)
                LOG.debug('Saved credentials')
            except HTTPError as e:
                if e.response.status_code == 401:
                    LOG.error('Could not refresh token, invalid refresh code.')
                else:
                    raise

            finally:
                identity_lock.release()
        else:  # Someone is updating the identity wait for release
            with identity_lock:
                LOG.debug('Refresh is already in progress, waiting until done')
                time.sleep(1.2)
                os.sync()
                self.identity = IdentityManager.load(lock=False)
                LOG.debug('new credentials loaded')

    def send(self, params, no_refresh=False):
        """ Send request to mycroft backend.
        The method handles Etags and will return a cached response value
        if nothing has changed on the remote.

        Arguments:
            params (dict): request parameters
            no_refresh (bool): optional parameter to disable refreshs of token

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
            # Etag matched, use response previously cached
            response = self.etag_to_response[etag]
        elif 'ETag' in response.headers:
            etag = response.headers['ETag'].strip('"')
            # Cache response for future lookup when we receive a 304
            self.params_to_etag[params_key] = etag
            self.etag_to_response[etag] = response

        return self.get_response(response, no_refresh)

    def get_response(self, response, no_refresh=False):
        """ Parse response and extract data from response.

        Will try to refresh the access token if it's expired.

        Arguments:
            response (requests Response object): Response to parse
            no_refresh (bool): Disable refreshing of the token
        Returns:
            data fetched from server
        """
        data = self.get_data(response)

        if 200 <= response.status_code < 300:
            return data
        elif (not no_refresh and response.status_code == 401 and not
                response.url.endswith("auth/token") and
                self.identity.is_expired()):
            self.refresh_token()
            return self.send(self.old_params, no_refresh=True)
        raise HTTPError(data, response=response)

    def get_data(self, response):
        try:
            return response.json()
        except Exception:
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
            for k, v in json.items():
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
            "path": "/" + UUID,
            "json": {"coreVersion": version.get("coreVersion"),
                     "platform": platform,
                     "platform_build": platform_build,
                     "enclosureVersion": version.get("enclosureVersion")}
        })

    def send_email(self, title, body, sender):
        return self.request({
            "method": "PUT",
            "path": "/" + UUID + "/message",
            "json": {"title": title, "body": body, "sender": sender}
        })

    def report_metric(self, name, data):
        return self.request({
            "method": "POST",
            "path": "/" + UUID + "/metric/" + name,
            "json": data
        })

    def get(self):
        """ Retrieve all device information from the web backend """
        return self.request({
            "path": "/" + UUID
        })

    def get_settings(self):
        """ Retrieve device settings information from the web backend

        Returns:
            str: JSON string with user configuration information.
        """
        return self.request({
            "path": "/" + UUID + "/setting"
        })

    def get_location(self):
        """ Retrieve device location information from the web backend

        Returns:
            str: JSON string with user location.
        """
        return self.request({
            "path": "/" + UUID + "/location"
        })

    def get_subscription(self):
        """
            Get information about type of subscrition this unit is connected
            to.

            Returns: dictionary with subscription information
        """
        return self.request({
            'path': '/' + UUID + '/subscription'})

    @property
    def is_subscriber(self):
        """
            status of subscription. True if device is connected to a paying
            subscriber.
        """
        try:
            return self.get_subscription().get('@type') != 'free'
        except Exception:
            # If can't retrieve, assume not paired and not a subscriber yet
            return False

    def get_subscriber_voice_url(self, voice=None):
        self.check_token()
        archs = {'x86_64': 'x86_64', 'armv7l': 'arm', 'aarch64': 'arm'}
        arch = archs.get(get_arch())
        if arch:
            path = '/' + UUID + '/voice?arch=' + arch
            return self.request({'path': path})['link']

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
            "path": "/" + UUID + "/token/" + str(dev_cred)
        })

    def get_skill_settings(self):
        """Get the remote skill settings for all skills on this device."""
        return self.request({
            "method": "GET",
            "path": "/" + UUID + "/skill/settings",
        })

    def upload_skill_metadata(self, settings_meta):
        """Upload skill metadata.

        Arguments:
            settings_meta (dict): skill info and settings in JSON format
        """
        return self.request({
            "method": "PUT",
            "path": "/" + UUID + "/settingsMeta",
            "json": settings_meta
        })

    def upload_skills_data(self, data):
        """ Upload skills.json file. This file contains a manifest of installed
        and failed installations for use with the Marketplace.

        Arguments:
             data: dictionary with skills data from msm
        """
        if not isinstance(data, dict):
            raise ValueError('data must be of type dict')

        # Strip the skills.json down to the bare essentials
        to_send = {}
        if 'blacklist' in data:
            to_send['blacklist'] = data['blacklist']
        else:
            LOG.warning('skills manifest lacks blacklist entry')
            to_send['blacklist'] = []

        # Make sure skills doesn't contain duplicates (keep only last)
        if 'skills' in data:
            skills = {s['name']: s for s in data['skills']}
            to_send['skills'] = [skills[key] for key in skills]
        else:
            LOG.warning('skills manifest lacks skills entry')
            to_send['skills'] = []

        for s in to_send['skills']:
            # Remove optional fields backend objects to
            if 'update' in s:
                s.pop('update')

            # Finalize skill_gid with uuid if needed
            s['skill_gid'] = s.get('skill_gid', '').replace(
                '@|', '@{}|'.format(self.identity.uuid))

        self.request({
            "method": "PUT",
            "path": "/" + UUID + "/skillJson",
            "json": to_send
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
    """Determine if this device is actively paired with a web backend

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

    api = DeviceApi()
    _paired_cache = api.identity.uuid and check_remote_pairing(ignore_errors)

    return _paired_cache


def check_remote_pairing(ignore_errors):
    """Check that a basic backend endpoint accepts our pairing.

    Arguments:
        ignore_errors (bool): True if errors should be ignored when

    Returns:
        True if pairing checks out, otherwise False.
    """
    try:
        DeviceApi().get()
        return True
    except HTTPError as e:
        if e.response.status_code == 401:
            return False
        error = e
    except Exception as e:
        error = e

    LOG.warning('Could not get device info: {}'.format(repr(error)))

    if ignore_errors:
        return False

    if isinstance(error, HTTPError):
        if connected():
            raise BackendDown from error
        else:
            raise InternetDown from error
    else:
        raise error
