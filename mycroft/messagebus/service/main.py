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
from tornado import autoreload, web, ioloop

from mycroft.configuration import Configuration
from mycroft.lock import Lock  # creates/supports PID locking file
from mycroft.messagebus.service.ws import WebsocketEventHandler
from mycroft.util import validate_param
from mycroft.util.log import LOG
from mycroft.messagebus.service.self_signed import create_self_signed_cert
from os.path import dirname, join


settings = {
    'debug': True
}


def main():
    import tornado.options
    lock = Lock("service")
    tornado.options.parse_command_line()

    def reload_hook():
        """ Hook to release lock when autoreload is triggered. """
        lock.delete()

    autoreload.add_reload_hook(reload_hook)

    config = Configuration.get().get("websocket")

    host = config.get("host")
    port = config.get("port")
    route = config.get("route")
    ssl = config.get("ssl", False)

    validate_param(host, "websocket.host")
    validate_param(port, "websocket.port")
    validate_param(route, "websocket.route")

    routes = [
        (route, WebsocketEventHandler)
    ]
    application = web.Application(routes, **settings)

    ssl_options = None
    if ssl:
        cert = config.get("cert", join(dirname(__file__), "certs",
                                       "secure_websocket.crt"))
        key = config.get("key", join(dirname(__file__), "certs",
                                     "secure_websocket.key"))
        self_sign = config.get("cert_auto_gen", True)
        if self_sign and (not key or not cert):
            LOG.error("ssl keys dont exist, creating self signed")
            cert_dir = join(dirname(__file__) , "certs")
            name = "secure_websocket"
            create_self_signed_cert(cert_dir, name)
            cert = join(cert_dir , name + ".crt")
            key = join(cert_dir , name + ".key")
            LOG.info("key created at: " + key)
            LOG.info("crt created at: " + cert)
            # TODO update and save config with new keys
            config["cert_file"] = cert
            config["key_file"] = key
        if key and cert:
            LOG.info("using ssl key at " + key)
            LOG.info("using ssl certificate at " + cert)
            ssl_options = {"certfile": cert, "keyfile": key}

    if ssl_options:
        LOG.info("wss connection started")
        application.listen(port, host, ssl_options=ssl_options)
    else:
        LOG.info("ws connection started")
        application.listen(port, host)
    ioloop.IOLoop.instance().start()


if __name__ == "__main__":
    main()
