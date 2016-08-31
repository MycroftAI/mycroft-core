import requests

from mycroft.configuration import ConfigurationManager
from mycroft.identity import IdentityManager


class Api(object):
    def __init__(self, path):
        self.path = path
        config = ConfigurationManager.get()
        config_server = config.get("server")
        self.url = config_server.get("url")
        self.version = config_server.get("version")
        self.identity = IdentityManager().get()

    def request(self, params):
        method = params.get("method", "GET")
        headers = self.build_headers(params)
        body = self.build_body(params)
        url = self.build_url(params)
        return requests.request(method, url, headers=headers, data=body)

    def build_headers(self, params):
        headers = params.get("headers", {})
        self.add_content_type(headers)
        self.add_authorization(headers)
        return headers

    def add_content_type(self, headers):
        if not headers["Content-Type"]:
            headers["Content-Type"] = "application/json"

    def add_authorization(self, headers):
        if not headers["Authorization"]:
            headers["Authorization"] = "Bearer " + self.identity.token

    def build_body(self, params):
        body = params.get("body")
        if body and params["headers"]["Content-Type"] == "application/json":
            for k, v in body:
                if v == "":
                    body[k] = None
        return body

    def build_url(self, params):
        path = params.get("path", "")
        version = params.get("version", self.version)
        return self.url + "/" + version + "/" + self.path + path


class DeviceApi(Api):
    def __init__(self):
        super(DeviceApi, self).__init__("device")

    def find_setting(self):
        params = {"path": "/" + self.identity.device_id + "/setting"}
        return self.request(params)
