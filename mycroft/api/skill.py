from mycroft.api import Api

__author__ = 'jdorleans'


class WAApi(Api):
    def __init__(self):
        super(WAApi, self).__init__("wa")

    def query(self, input):
        return self.request({
            "path": "?input=" + input
        })


class OWMApi(Api):
    def __init__(self):
        super(OWMApi, self).__init__("owm")

    def query(self, path):
        return self.request({
            "path": path
        })
