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
from os.path import expanduser, exists, abspath, dirname
import sys
import time

from mycroft.configuration import ConfigurationManager
from mycroft.messagebus.client.ws import WebsocketClient
from mycroft.util.log import getLogger

__author__ = 'forslund'

sys.path.append(abspath(dirname(__file__)))
logger = getLogger("Audio")

ws = None

default = None
service = []
current = None

def load_services_callback():
    global ws
    global default
    global service

    config = ConfigurationManager.get().get("Audio")
    logger.info("Loading services")
    # only import services that are configured
    from services.mpg123_service import Mpg123Service
    from services.mopidy_service import MopidyService
    for b in config['backends']:
        logger.debug(b)
        b = config['backends'][b]
        if b['type'] == 'vlc' and b.get('active', False):
            from services.vlc_service import VlcService
        if b['type'] == 'chromecast' and b.get('active', False):
            from services.chromecast_service import ChromecastService

    if config.get('autodetect-chromecasts', False):
        autodetect_chromecasts = __import__('chromecast_service').autodetect


    # Add all manually specified services
    for name in config['backends']:
        b = config['backends'][name]
        logger.debug(b)
        if b['type'] == 'vlc' and b.get('active', False):
            logger.info('starting VLC service')
            service.append(VlcService(b, ws, name))
        if b['type'] == 'mopidy' and b.get('active', False):
            logger.info('starting Mopidy service')
            service.append(MopidyService(b, ws, name))
        if b['type'] == 'mpg123' and b.get('active', False):
            logger.info('starting Mpg123 service')
            service.append(Mpg123Service(b, ws, name))
        if b['type'] == 'chromecast' and b.get('active', False):
            logger.info('starting Chromecast service')
            service.append(ChromecastService(b, ws, name))

    # Autodetect chromecast devices
    if config.get('autodetect-chromecasts', False):
        logger.info('Autodetecting Chromecasts')
        chromecasts = autodetect_chromecasts({}, ws)
        service = service + chromecasts

    default_name = config.get('default-backend', '')
    for s in service:
        if s.name == default_name:
            default = s
            break
    else:
        default = None
    logger.info(default)

    ws.on('MycroftAudioServicePlay', _play)
    ws.on('MycroftAudioServicePause', _pause)
    ws.on('MycroftAudioServiceStop', _stop)
    ws.on('MycroftAudioServiceNext', _next)
    ws.on('MycroftAudioServicePrev', _prev)
    ws.on('MycroftAudioServiceTrackInfo', _track_info)
    ws.on('recognizer_loop:audio_output_start', _lower_volume)
    ws.on('recognizer_loop:audio_output_end', _restore_volume)


def _pause(message=None):
    global current
    if current:
        current.pause()


def _next(message=None):
    global current
    if current:
        current.next()


def _prev(message=None):
    global current
    if current:
        current.prev()


def _stop(message=None):
    global current
    logger.info('stopping all playing services')
    print current
    if current:
        current.stop()
        current = None
    logger.info('Stopped')


def _lower_volume(message):
    global current
    global volume_is_low
    logger.info('lowering volume')
    if current:
        current.lower_volume()
        volume_is_low = True

def _restore_volume(message):
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
    global service
    logger.info('MycroftAudioServicePlay')
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
    global current
    if current:
        track_info = self.current.track_info()
    else:
        track_info = {}
    self.emitter.emit(Message('MycroftAudioServiceTrackInfoReply',
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

            if _message.get("type") == "registration":
                # do not log tokens from registration messages
                _message["data"]["token"] = None
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
