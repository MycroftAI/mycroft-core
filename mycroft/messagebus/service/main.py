# Copyright 2016 Mycroft AI, Inc.
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
from tornado import autoreload, web, ioloop

from mycroft.configuration import Configuration
from mycroft.lock import Lock  # creates/supports PID locking file
from mycroft.messagebus.service.ws import WebsocketEventHandler
from mycroft.util import validate_param
from mycroft.util.log import LOG
from mycroft.messagebus.service.self_signed import create_self_signed_cert
from os.path import dirname

__author__ = 'seanfitz', 'jdorleans'

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
        cert = config.get("cert")
        key = config.get("key")
        self_sign = config.get("cert_auto_gen")
        if self_sign and (not key or not cert):
            LOG.error("ssl keys dont exist, creating self signed")
            dir = dirname(__file__) + "/certs"
            name = "secure_websocket"
            create_self_signed_cert(dir, name)
            cert = dir + "/" + name + ".crt"
            key = dir + "/" + name + ".key"
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
