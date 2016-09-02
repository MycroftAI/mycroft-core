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
        self.identity = IdentityManager().get()

    def request(self, params):
        method = params.get("method", "GET")
        headers = self.build_headers(params)
        body = self.build_body(params)
        url = self.build_url(params)
        response = requests.request(method, url, headers=headers, data=body)
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

    def build_body(self, params):
        body = params.get("body")
        if body and params["headers"]["Content-Type"] == "application/json":
            for k, v in body:
                if v == "":
                    body[k] = None
        params["body"] = body
        return body

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
            "path": "/" + self.identity.uuid + "/activate",
            "body": {"state": state, "token": token}
        })

    def find(self):
        return self.request({
            "path": "/" + self.identity.uuid
        })

    def find_setting(self):
        return self.request({
            "path": "/" + self.identity.uuid + "/setting"
        })
