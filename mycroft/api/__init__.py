import requests
from requests import HTTPError

from mycroft.configuration import ConfigurationManager
from mycroft.identity import IdentityManager

__author__ = 'jdorleans'


class Api(object):
    def __init__(self, path):
        self.path = path
        config = ConfigurationManager().get()
        config_server = config.get("server")
        self.url = config_server.get("url")
        self.version = config_server.get("version")
        self.identity = IdentityManager.get()

    def request(self, params):
        method = params.get("method", "GET")
        headers = self.build_headers(params)
        json = self.build_json(params)
        query = params.get("query")
        url = self.build_url(params)
        response = requests.request(method, url, headers=headers, params=query,
                                    data=params.get("data"), json=json)
        return self.get_response(response)

    @staticmethod
    def get_response(response):
        try:
            data = response.json()
        except:
            data = response.text

        if 200 <= response.status_code < 300:
            return data
        else:
            raise HTTPError(data, response=response)

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
            headers["Authorization"] = "Bearer " + self.identity.token

    def build_json(self, params):
        json = params.get("json")
        if json and params["headers"]["Content-Type"] == "application/json":
            for k, v in json.iteritems():
                if v == "":
                    json[k] = None
            params["json"] = json
        return json

    def build_url(self, params):
        path = params.get("path", "")
        version = params.get("version", self.version)
        return self.url + "/" + version + "/" + self.path + path


class DeviceApi(Api):
    def __init__(self):
        super(DeviceApi, self).__init__("device")

    def get_code(self, state):
        return self.request({
            "path": "/code?state=" + state
        })

    def activate(self, state, token):
        return self.request({
            "method": "POST",
            "path": "/activate",
            "json": {"state": state, "token": token}
        })

    def find(self):
        return self.request({
            "path": "/" + self.identity.uuid
        })

    def find_setting(self):
        return self.request({
            "path": "/" + self.identity.uuid + "/setting"
        })


class STTApi(Api):
    def __init__(self):
        super(STTApi, self).__init__("stt")

    def stt(self, audio, language):
        return self.request({
            "method": "POST",
            "headers": {"Content-Type": "audio/x-flac"},
            "query": {"lang": language},
            "data": audio
        })
