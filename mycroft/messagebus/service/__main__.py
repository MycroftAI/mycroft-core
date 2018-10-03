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
from mycroft.util import validate_param, reset_sigint_handler, create_daemon, \
    wait_for_exit_signal
from mycroft.util.log import LOG

settings = {
    'debug': True
}


def main():
    import tornado.options
    reset_sigint_handler()
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
        if not key or not cert:
            LOG.error("ssl keys dont exist, falling back to unsecured socket")

        else:
            LOG.info("using ssl key at " + key)
            LOG.info("using ssl certificate at " + cert)
            ssl_options = {"certfile": cert, "keyfile": key}
    if ssl_options:
        LOG.info("wss connection started")
        application.listen(port, host, ssl_options=ssl_options)
    else:
        LOG.info("ws connection started")
        application.listen(port, host)
    create_daemon(ioloop.IOLoop.instance().start)

    wait_for_exit_signal()


if __name__ == "__main__":
    main()
