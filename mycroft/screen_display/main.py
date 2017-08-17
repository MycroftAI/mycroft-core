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


import json
from os.path import abspath, dirname, basename, isdir, join
from os import listdir
import sys
import imp
from mycroft.configuration import ConfigurationManager
from mycroft.messagebus.client.ws import WebsocketClient
from mycroft.util.log import getLogger


__author__ = 'jarbas'

MainModule = '__init__'
sys.path.append(abspath(dirname(__file__)))
logger = getLogger("Display_Screen")

ws = None

default = None
services = []
current = None
config = None


def create_service_descriptor(service_folder):
    """Prepares a descriptor that can be used together with imp.

        Args:
            service_folder: folder that shall be imported.

        Returns:
            Dict with import information
    """
    info = imp.find_module(MainModule, [service_folder])
    return {"name": basename(service_folder), "info": info}


def get_services(services_folder):
    """
        Load and initialize services from all subfolders.

        Args:
            services_folder: base folder to look for services in.

        Returns:
            Sorted list of display services.
    """
    logger.info("Loading display services from " + services_folder)
    services = []
    possible_services = listdir(services_folder)
    for i in possible_services:
        location = join(services_folder, i)
        if (isdir(location) and
                not MainModule + ".py" in listdir(location)):
            for j in listdir(location):
                name = join(location, j)
                if (not isdir(name) or
                        not MainModule + ".py" in listdir(name)):
                    continue
                try:
                    services.append(create_service_descriptor(name))
                except:
                    logger.error('Failed to create service from ' + name,
                                 exc_info=True)
        if (not isdir(location) or
                not MainModule + ".py" in listdir(location)):
            continue
        try:
            services.append(create_service_descriptor(location))
        except:
            logger.error('Failed to create service from ' + name,
                         exc_info=True)
    return sorted(services, key=lambda p: p.get('name'))


def load_services(config, ws, path=None):
    """
        Search though the service directory and load any services.

        Args:
            config: configuration dicrt for the audio backends.
            ws: websocket object for communication.

        Returns:
            List of started services.
    """
    logger.info("Loading services")
    if path is None:
        path = dirname(abspath(__file__)) + '/services/'
    service_directories = get_services(path)
    service = []
    for descriptor in service_directories:
        logger.info('Loading ' + descriptor['name'])
        try:
            service_module = imp.load_module(descriptor["name"] + MainModule,
                                             *descriptor["info"])
        except:
            logger.error('Failed to import module ' + descriptor['name'],
                         exc_info=True)
            continue
        if (hasattr(service_module, 'autodetect') and
                callable(service_module.autodetect)):
            try:
                s = service_module.autodetect(config, ws)
                service += s
            except:
                logger.error('Failed to autodetect...',
                             exc_info=True)
        if (hasattr(service_module, 'load_service')):
            try:
                s = service_module.load_service(config, ws)
                service += s
            except:
                logger.error('Failed to load service...',
                             exc_info=True)

    return service


def load_services_callback():
    """
        Main callback function for loading services. Sets up the globals
        service and default and registers the event handlers for the subsystem.
    """
    global ws
    global default
    global services

    config = ConfigurationManager.get().get("Displays")
    services = load_services(config, ws)
    logger.info(services)
    default_name = config.get('default-backend', '')
    logger.info('Finding default backend...')
    for s in services:
        logger.info('checking ' + s.name)
        if s.name == default_name:
            default = s
            logger.info('Found ' + default.name)
            break
    else:
        default = None
        logger.info('no default found')
    logger.info('Default:' + str(default))

    ws.on('mycroft.display.service.lock', _lock)
    ws.on('mycroft.display.service.unlock', _unlock)
    ws.on('mycroft.display.service.clear', _clear)
    ws.on('mycroft.display.service.display', _display)
    ws.on('mycroft.display.service.reset', _reset)
    ws.on('mycroft.display.service.prev', _prev)
    ws.on('mycroft.display.service.next', _next)
    ws.on('mycroft.display.service.close', _close)
    ws.on('mycroft.display.service.width', _width)
    ws.on('mycroft.display.service.height', _height)
    ws.on('mycroft.display.service.fullscreen', _fullscreen)
    ws.on('mycroft.display.service.add_pictures', _add_pictures)
    ws.on('mycroft.stop', _stop)


def _stop(message=None):
    """
        Handler for mycroft.stop. Stops any display service.

        Args:
            message: message bus message, not used but required
    """
    global current
    logger.info('stopping all display services')
    if current:
        current.stop()
        current = None
    logger.info('Stopped')


def width(prefered_service, width=500):
    global current
    logger.info('Setting width')
    # check if user requested a particular service
    if prefered_service:
        service = prefered_service
    # check if default supports the uri
    elif default:
        logger.info("Using default backend")
        logger.info(default.name)
        service = default
    else:  # TODO Check if any other service can play the media
        return
    service.change_width(width)
    current = service


def _width(message):
    """
        Handler for mycroft.display.service.unlock. Allow display after
        a lock. Also  determines if the user requested a special service.

        Args:
            message: message bus message, not used but required
    """
    global services
    logger.info('mycroft.display.service.width')
    # Find if the user wants to use a specific backend
    for s in services:
        logger.info(s.name)
        if s.name in message.data['utterance']:
            prefered_service = s
            logger.info(s.name + ' would be prefered')
            break
    else:
        prefered_service = None
    width(prefered_service, message.data.get("width", 500))


def height(prefered_service, height=500):
    global current
    logger.info('Setting height')
    # check if user requested a particular service
    if prefered_service:
        service = prefered_service
    # check if default supports the uri
    elif default:
        logger.info("Using default backend")
        logger.info(default.name)
        service = default
    else:  # TODO Check if any other service can play the media
        return
    service.change_height(height)
    current = service


def _height(message):
    """
        Handler for mycroft.display.service.unlock. Allow display after
        a lock. Also  determines if the user requested a special service.

        Args:
            message: message bus message, not used but required
    """
    global services
    logger.info('mycroft.display.service.height')
    # Find if the user wants to use a specific backend
    for s in services:
        logger.info(s.name)
        if s.name in message.data['utterance']:
            prefered_service = s
            logger.info(s.name + ' would be prefered')
            break
    else:
        prefered_service = None
    height(prefered_service, message.data.get("height", 500))


def fullscreen(prefered_service):
    global current
    logger.info('Setting fullscreen')
    # check if user requested a particular service
    if prefered_service:
        service = prefered_service
    # check if default supports the uri
    elif default:
        logger.info("Using default backend")
        logger.info(default.name)
        service = default
    else:  # TODO Check if any other service can play the media
        return
    service.change_fullscreen()
    current = service


def _fullscreen(message):
    """
        Handler for mycroft.display.service.fullscreen. Also  determines 
        if the user requested a special service.

        Args:
            message: message bus message, not used but required
    """
    global services
    logger.info('mycroft.display.service.fullscreen')
    # Find if the user wants to use a specific backend
    for s in services:
        logger.info(s.name)
        if s.name in message.data['utterance']:
            prefered_service = s
            logger.info(s.name + ' would be prefered')
            break
    else:
        prefered_service = None
    fullscreen(prefered_service)


def unlock(prefered_service):
    global current
    logger.info('Unlocking Display')
    # check if user requested a particular service
    if prefered_service:
        service = prefered_service
    # check if default supports the uri
    elif default:
        logger.info("Using default backend")
        logger.info(default.name)
        service = default
    else:  # TODO Check if any other service can play the media
        return
    service.unlock()
    current = service


def _unlock(message):
    """
        Handler for mycroft.display.service.unlock. Allow display after
        a lock. Also  determines if the user requested a special service.

        Args:
            message: message bus message, not used but required
    """
    global services
    logger.info('mycroft.display.service.unlock')
    # Find if the user wants to use a specific backend
    for s in services:
        logger.info(s.name)
        if s.name in message.data['utterance']:
            prefered_service = s
            logger.info(s.name + ' would be prefered')
            break
    else:
        prefered_service = None
    unlock(prefered_service)


def lock(prefered_service):
    global current
    logger.info('Locking Display')
    # check if user requested a particular service
    if prefered_service:
        service = prefered_service
    # check if default supports the uri
    elif default:
        logger.info("Using default backend")
        logger.info(default.name)
        service = default
    else:  # TODO Check if any other service can play the media
        return
    service.lock()
    current = service


def _lock(message):
    """
        Handler for mycroft.display.service.lock. Do not allow display until
        unlock. Also  determines if the user requested a special service.

        Args:
            message: message bus message, not used but required
    """
    global services
    logger.info('mycroft.display.service.lock')

    # Find if the user wants to use a specific backend
    for s in services:
        logger.info(s.name)
        if s.name in message.data['utterance']:
            prefered_service = s
            logger.info(s.name + ' would be prefered')
            break
    else:
        prefered_service = None
    lock(prefered_service)


def add_pictures(prefered_service, picture_list):
    global current
    logger.info('Add pictures Display')
    # check if user requested a particular service
    if prefered_service:
        service = prefered_service
    # check if default supports the uri
    elif default:
        logger.info("Using default backend")
        logger.info(default.name)
        service = default
    else:  # TODO Check if any other service can play the media
        return
    service.add_pictures(picture_list)
    current = service


def _add_pictures(message):
    """
        Handler for mycroft.display.service.display. Starts display of a
        picture. Also  determines if the user requested a special service.

        Args:
            message: message bus message, not used but required
    """
    global services
    logger.info('mycroft.display.service.add_pictures')
    # Find if the user wants to use a specific backend
    for s in services:
        logger.info(s.name)
        if s.name in message.data['utterance']:
            prefered_service = s
            logger.info(s.name + ' would be prefered')
            break
    else:
        prefered_service = None
    picture_list = message.data.get("file_list", [])
    add_pictures(prefered_service, picture_list)


def close(prefered_service):
    global current
    logger.info('Close Display')
    # check if user requested a particular service
    if prefered_service:
        service = prefered_service
    # check if default supports the uri
    elif default:
        logger.info("Using default backend")
        logger.info(default.name)
        service = default
    else:  # TODO Check if any other service can play the media
        return
    service.close()
    current = service


def _close(message):
    """
        Handler for mycroft.display.service.display. Starts display of a
        picture. Also  determines if the user requested a special service.

        Args:
            message: message bus message, not used but required
    """
    global services
    logger.info('mycroft.display.service.close')
    # Find if the user wants to use a specific backend
    for s in services:
        logger.info(s.name)
        if s.name in message.data['utterance']:
            prefered_service = s
            logger.info(s.name + ' would be prefered')
            break
    else:
        prefered_service = None
    close(prefered_service)

def next(prefered_service):
    global current
    logger.info('Next Display')
    # check if user requested a particular service
    if prefered_service:
        service = prefered_service
    # check if default supports the uri
    elif default:
        logger.info("Using default backend")
        logger.info(default.name)
        service = default
    else:  # TODO Check if any other service can play the media
        return
    service.next()
    current = service


def _next(message):
    """
        Handler for mycroft.display.service.display. Starts display of a
        picture. Also  determines if the user requested a special service.

        Args:
            message: message bus message, not used but required
    """
    global services
    logger.info('mycroft.display.service.next')
    # Find if the user wants to use a specific backend
    for s in services:
        logger.info(s.name)
        if s.name in message.data['utterance']:
            prefered_service = s
            logger.info(s.name + ' would be prefered')
            break
    else:
        prefered_service = None
    prev(prefered_service)


def prev(prefered_service):
    global current
    logger.info('Previous Display')
    # check if user requested a particular service
    if prefered_service:
        service = prefered_service
    # check if default supports the uri
    elif default:
        logger.info("Using default backend")
        logger.info(default.name)
        service = default
    else:  # TODO Check if any other service can play the media
        return
    service.previous()
    current = service


def _prev(message):
    """
        Handler for mycroft.display.service.display. Starts display of a
        picture. Also  determines if the user requested a special service.

        Args:
            message: message bus message, not used but required
    """
    global services
    logger.info('mycroft.display.service.prev')
    # Find if the user wants to use a specific backend
    for s in services:
        logger.info(s.name)
        if s.name in message.data['utterance']:
            prefered_service = s
            logger.info(s.name + ' would be prefered')
            break
    else:
        prefered_service = None
    prev(prefered_service)


def display(file_path_list, reset, prefered_service):
    global current
    logger.info('Display')
    # check if user requested a particular service
    if prefered_service:
        service = prefered_service
    # check if default supports the uri
    elif default:
        logger.info("Using default backend")
        logger.info(default.name)
        service = default
    else:  # TODO Check if any other service can play the media
        return
    if reset:
        logger.info("Reseting service pic list")
        service.reset()
    logger.info('Add picture paths: ' + str(file_path_list))
    service.add_pictures(file_path_list)
    logger.info('Displaying')
    service.display()
    current = service


def _display(message):
    """
        Handler for mycroft.display.service.display. Starts display of a
        picture. Also  determines if the user requested a special service.

        Args:
            message: message bus message, not used but required
    """
    global services
    logger.info('mycroft.display.service.display')
    logger.info(message.data['file_list'])

    file_list = message.data['file_list']
    reset = message.data.get("reset", True)
    # Find if the user wants to use a specific backend
    for s in services:
        logger.info(s.name)
        if s.name in message.data['utterance']:
            prefered_service = s
            logger.info(s.name + ' would be prefered')
            break
    else:
        prefered_service = None
    display(file_list, reset, prefered_service)


def clear(prefered_service):
    global current
    logger.info('Clearing Display')
    # check if user requested a particular service
    if prefered_service:
        service = prefered_service
    # check if default supports the uri
    elif default:
        logger.info("Using default backend")
        logger.info(default.name)
        service = default
    else:  # TODO Check if any other service can play the media
        return
    service.clear()
    current = service


def _clear(message):
    """
        Handler for mycroft.display.service.clear.Clears display.
        Also  determines if the user requested a special service.

        Args:
            message: message bus message, not used but required
    """
    global services
    logger.info('mycroft.display.service.clear')

    # Find if the user wants to use a specific backend
    for s in services:
        logger.info(s.name)
        if s.name in message.data['utterance']:
            prefered_service = s
            logger.info(s.name + ' would be prefered')
            break
    else:
        prefered_service = None
    clear(prefered_service)


def reset(prefered_service):
    global current
    logger.info('Reseting Display')
    # check if user requested a particular service
    if prefered_service:
        service = prefered_service
    # check if default supports the uri
    elif default:
        logger.info("Using default backend")
        logger.info(default.name)
        service = default
    else:  # TODO Check if any other service can play the media
        return
    service.reset()
    current = service


def _reset(message):
    """
        Handler for mycroft.display.service.reset.Resets display to default pic.
        Also  determines if the user requested a special service.

        Args:
            message: message bus message, not used but required
    """
    global services
    logger.info('mycroft.display.service.reset')

    # Find if the user wants to use a specific backend
    for s in services:
        logger.info(s.name)
        if s.name in message.data['utterance']:
            prefered_service = s
            logger.info(s.name + ' would be prefered')
            break
    else:
        prefered_service = None
    reset(prefered_service)


def connect():
    global ws
    ws.run_forever()


def main():
    global ws
    global config
    ws = WebsocketClient()
    ConfigurationManager.init(ws)
    config = ConfigurationManager.get()

    def echo(message):
        accept = ["display"]
        try:
            _message = json.loads(message)
            message = json.dumps(_message)
            for type in accept:
                if type in _message.get('type'):
                    logger.debug(message)
        except:
            pass

    logger.info("Starting Display Services")
    ws.on('message', echo)
    ws.once('open', load_services_callback)
    try:
        ws.run_forever()
    except KeyboardInterrupt, e:
        logger.exception(e)
        sys.exit()


if __name__ == "__main__":
    main()
