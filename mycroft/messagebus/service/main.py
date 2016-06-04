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

import tornado.ioloop as ioloop
import tornado.web as web

from mycroft.configuration.config import ConfigurationManager
from mycroft.messagebus.service.ws import WebsocketEventHandler

__author__ = 'seanfitz'

settings = {
    'debug': True
}


def main():
    import tornado.options
    tornado.options.parse_command_line()
    config = ConfigurationManager.get_config()
    service_config = config.get("messagebus_service")

    routes = [
        (service_config.get('route'), WebsocketEventHandler)
    ]

    application = web.Application(routes, **settings)

    application.listen(service_config.get("port"), service_config.get("host"))
    loop = ioloop.IOLoop.instance()
    loop.start()


if __name__ == "__main__":
    main()
