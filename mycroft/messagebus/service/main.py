import tornado.ioloop
import tornado.web

from mycroft.messagebus.service.ws import WebsocketEventHandler
from mycroft.configuration.config import ConfigurationManager

__author__ = 'seanfitz'

settings = {
    'debug': True
}


def main():
    import tornado.options
    tornado.options.parse_command_line()
    ConfigurationManager.load()
    config = ConfigurationManager.get_config()
    service_config = config.get("messagebus_service")

    routes = [
        (service_config.get('route'), WebsocketEventHandler)
    ]

    application = tornado.web.Application(routes, **settings)

    application.listen(service_config.get("port"), service_config.get("host"))
    ioloop = tornado.ioloop.IOLoop.instance()
    ioloop.start()


if __name__ == "__main__":
    main()
