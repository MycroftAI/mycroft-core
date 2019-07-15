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
"""Mycroft core message bus service."""
from tornado import autoreload, web, ioloop

from mycroft.configuration import Configuration
from mycroft.lock import Lock  # creates/supports PID locking file
from mycroft.messagebus.service.event_handler import MessageBusEventHandler
from mycroft.util import (
    reset_sigint_handler,
    create_daemon,
    wait_for_exit_signal
)
from mycroft.util.log import LOG


def _load_message_bus_configs():
    LOG.info('Loading message bus configs')
    config = Configuration.get()

    try:
        websocket_configs = config['websocket']
    except KeyError as ke:
        LOG.error('No websocket configs found')
        LOG.exception(ke)
        raise
    else:
        try:
            host = websocket_configs['host']
            port = websocket_configs['port']
            route = websocket_configs['route']
        except KeyError as ke:
            LOG.error('Missing one or more websocket configs')
            LOG.exception(ke)
            raise
    LOG.info(
        'Config values loaded: \n\thost: {}\n\tport: {}\n\troute: {}'.format(
            host, port, route
        )
    )
    return host, port, route


def main():
    import tornado.options
    LOG.info('Starting message bus service...')
    reset_sigint_handler()
    lock = Lock("service")
    tornado.options.parse_command_line()

    def reload_hook():
        """ Hook to release lock when auto reload is triggered. """
        lock.delete()

    autoreload.add_reload_hook(reload_hook)
    host, port, route = _load_message_bus_configs()
    routes = [(route, MessageBusEventHandler)]
    application = web.Application(routes, debug=True)
    application.listen(port, host)
    create_daemon(ioloop.IOLoop.instance().start)
    LOG.info('Message bus service started!')
    wait_for_exit_signal()


if __name__ == "__main__":
    main()
