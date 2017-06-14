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
from os.path import expanduser, exists, abspath, dirname, basename, isdir, join
from os import listdir
import sys
import time
import imp

from mycroft.configuration import ConfigurationManager
from mycroft.messagebus.client.ws import WebsocketClient
from mycroft.util.log import getLogger

__author__ = 'forslund'

MainModule = '__init__'
sys.path.append(abspath(dirname(__file__)))
logger = getLogger("Audio")

ws = None

default = None
service = []
current = None


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
            Sorted list of audio services.
    """
    logger.info("Loading skills from " + services_folder)
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


def load_services(config, ws):
    """
        Search though the service directory and load any services.

        Args:
            config: configuration dicrt for the audio backends.
            ws: websocket object for communication.

        Returns:
            List of started services.
    """
    logger.info("Loading services")
    service_directories = get_services(dirname(abspath(__file__)) +
                                       '/services/')
    service = []
    for descriptor in service_directories:
        logger.info('Loading ' + descriptor['name'])
        try:
            service_module = imp.load_module(descriptor["name"] + MainModule,
                                             *descriptor["info"])
        except:
            logger.error('Failed to import module ' + descriptor['name'],
                         exc_info=True)
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
    global service

    config = ConfigurationManager.get().get("Audio")
    service = load_services(config, ws)
    logger.info(service)
    default_name = config.get('default-backend', '')
    logger.info('Finding default backend...')
    for s in service:
        logger.info('checking ' + s.name)
        if s.name == default_name:
            default = s
            logger.info('Found ' + default.name)
            break
    else:
        default = None
        logger.info('no default found')
    logger.info('Default:' + str(default))

    ws.on('mycroft.audio.service.play', _play)
    ws.on('mycroft.audio.service.pause', _pause)
    ws.on('mycroft.audio.service.resume', _resume)
    ws.on('mycroft.audio.service.stop', _stop)
    ws.on('mycroft.audio.service.next', _next)
    ws.on('mycroft.audio.service.prev', _prev)
    ws.on('mycroft.audio.service.track_info', _track_info)
    ws.on('recognizer_loop:audio_output_start', _lower_volume)
    ws.on('recognizer_loop:audio_output_end', _restore_volume)

    ws.on('mycroft.stop', _stop)


def _pause(message=None):
    """
        Handler for mycroft.audio.service.pause. Pauses the current audio
        service.

        Args:
            message: message bus message, not used but required
    """
    global current
    if current:
        current.pause()


def _resume(message=None):
    """
        Handler for mycroft.audio.service.resume.

        Args:
            message: message bus message, not used but required
    """
    global current
    if current:
        current.resume()


def _next(message=None):
    """
        Handler for mycroft.audio.service.next. Skips current track and
        starts playing the next.

        Args:
            message: message bus message, not used but required
    """
    global current
    if current:
        current.next()


def _prev(message=None):
    """
        Handler for mycroft.audio.service.prev. Starts playing the previous
        track.

        Args:
            message: message bus message, not used but required
    """
    global current
    if current:
        current.prev()


def _stop(message=None):
    """
        Handler for mycroft.stop. Stops any playing service.

        Args:
            message: message bus message, not used but required
    """
    global current
    logger.info('stopping all playing services')
    if current:
        current.stop()
        current = None
    logger.info('Stopped')


def _lower_volume(message):
    """
        Is triggered when mycroft starts to speak and reduces the volume.

        Args:
            message: message bus message, not used but required
    """
    global current
    global volume_is_low
    logger.info('lowering volume')
    if current:
        current.lower_volume()
        volume_is_low = True


def _restore_volume(message):
    """
        Is triggered when mycroft is done speaking and restores the volume

        Args:
            message: message bus message, not used but required
    """
    global current
    global volume_is_low
    logger.info('maybe restoring volume')
    if current:
        volume_is_low = False
        time.sleep(2)
        if not volume_is_low:
            logger.info('restoring volume')
            current.restore_volume()


def play(tracks, prefered_service):
    """
        play starts playing the audio on the prefered service if it supports
        the uri. If not the next best backend is found.

        Args:
            tracks: list of tracks to play.
            prefered_service: indecates the service the user prefer to play
                              the tracks.
    """
    global current
    logger.info('play')
    _stop()
    uri_type = tracks[0].split(':')[0]
    logger.info('uri_type: ' + uri_type)
    # check if user requested a particular service
    if prefered_service and uri_type in prefered_service.supported_uris():
        service = prefered_service
    # check if default supports the uri
    elif default and uri_type in default.supported_uris():
        logger.info("Using default backend")
        logger.info(default.name)
        service = default
    else:  # Check if any other service can play the media
        for s in service:
            logger.info(str(s))
            if uri_type in s.supported_uris():
                service = s
                break
        else:
            return
    logger.info('Clear list')
    service.clear_list()
    logger.info('Add tracks' + str(tracks))
    service.add_list(tracks)
    logger.info('Playing')
    service.play()
    current = service


def _play(message):
    """
        Handler for mycroft.audio.service.play. Starts playback of a
        tracklist. Also  determines if the user requested a special service.

        Args:
            message: message bus message, not used but required
    """
    global service
    logger.info('mycroft.audio.service.play')
    logger.info(message.data['tracks'])

    tracks = message.data['tracks']

    # Find if the user wants to use a specific backend
    for s in service:
        logger.info(s.name)
        if s.name in message.data['utterance']:
            prefered_service = s
            logger.info(s.name + ' would be prefered')
            break
    else:
        prefered_service = None
    play(tracks, prefered_service)


def _track_info(message):
    """
        Returns track info on the message bus.

        Args:
            message: message bus message, not used but required
    """
    global current
    if current:
        track_info = self.current.track_info()
    else:
        track_info = {}
    self.emitter.emit(Message('mycroft.audio.service.track_info_reply',
                              data=track_info))


def connect():
    global ws
    ws.run_forever()


def main():
    global ws
    ws = WebsocketClient()
    ConfigurationManager.init(ws)

    def echo(message):
        try:
            _message = json.loads(message)

            if 'mycroft.audio.service' in _message.get('type'):
                return
            message = json.dumps(_message)
        except:
            pass
        logger.debug(message)

    logger.info("Staring Audio Services")
    ws.on('message', echo)
    ws.once('open', load_services_callback)
    ws.run_forever()


if __name__ == "__main__":
    main()
