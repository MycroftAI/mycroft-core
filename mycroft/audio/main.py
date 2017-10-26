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
import imp
import json
import sys
import time

from os import listdir
from os.path import abspath, dirname, basename, isdir, join

import mycroft.audio.speech as speech
from mycroft.configuration import Configuration
from mycroft.messagebus.client.ws import WebsocketClient
from mycroft.messagebus.message import Message
from mycroft.util.log import LOG

try:
    import pulsectl
except:
    pulsectl = None


MainModule = '__init__'
sys.path.append(abspath(dirname(__file__)))

ws = None

default = None
service = []
current = None
config = None
pulse = None
pulse_quiet = None
pulse_restore = None


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
    LOG.info("Loading skills from " + services_folder)
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
                    LOG.error('Failed to create service from ' + name,
                              exc_info=True)
        if (not isdir(location) or
                not MainModule + ".py" in listdir(location)):
            continue
        try:
            services.append(create_service_descriptor(location))
        except:
            LOG.error('Failed to create service from ' + name,
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
    LOG.info("Loading services")
    if path is None:
        path = dirname(abspath(__file__)) + '/services/'
    service_directories = get_services(path)
    service = []
    for descriptor in service_directories:
        LOG.info('Loading ' + descriptor['name'])
        try:
            service_module = imp.load_module(descriptor["name"] + MainModule,
                                             *descriptor["info"])
        except:
            LOG.error('Failed to import module ' + descriptor['name'],
                      exc_info=True)
        if (hasattr(service_module, 'autodetect') and
                callable(service_module.autodetect)):
            try:
                s = service_module.autodetect(config, ws)
                service += s
            except:
                LOG.error('Failed to autodetect...',
                          exc_info=True)
        if (hasattr(service_module, 'load_service')):
            try:
                s = service_module.load_service(config, ws)
                service += s
            except:
                LOG.error('Failed to load service...',
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

    config = Configuration.get().get("Audio")
    service = load_services(config, ws)
    LOG.info(service)
    default_name = config.get('default-backend', '')
    LOG.info('Finding default backend...')
    for s in service:
        LOG.info('checking ' + s.name)
        if s.name == default_name:
            default = s
            LOG.info('Found ' + default.name)
            break
    else:
        default = None
        LOG.info('no default found')
    LOG.info('Default:' + str(default))

    ws.on('mycroft.audio.service.play', _play)
    ws.on('mycroft.audio.service.pause', _pause)
    ws.on('mycroft.audio.service.resume', _resume)
    ws.on('mycroft.audio.service.stop', _stop)
    ws.on('mycroft.audio.service.next', _next)
    ws.on('mycroft.audio.service.prev', _prev)
    ws.on('mycroft.audio.service.track_info', _track_info)
    ws.on('recognizer_loop:audio_output_start', _lower_volume)
    ws.on('recognizer_loop:record_begin', _lower_volume)
    ws.on('recognizer_loop:audio_output_end', _restore_volume)
    ws.on('recognizer_loop:record_end', _restore_volume)
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
    LOG.info('stopping all playing services')
    if current:
        current.stop()
        current = None
    LOG.info('Stopped')


def _lower_volume(message):
    """
        Is triggered when mycroft starts to speak and reduces the volume.

        Args:
            message: message bus message, not used but required
    """
    global current
    global volume_is_low
    LOG.info('lowering volume')
    if current:
        current.lower_volume()
        volume_is_low = True
    try:
        if pulse_quiet:
            pulse_quiet()
    except Exception as e:
        LOG.error(e)


muted_sinks = []


def pulse_mute():
    """
        Mute all pulse audio input sinks except for the one named
        'mycroft-voice'.
    """
    global muted_sinks
    for sink in pulse.sink_input_list():
        if sink.name != 'mycroft-voice':
            pulse.sink_input_mute(sink.index, 1)
            muted_sinks.append(sink.index)


def pulse_unmute():
    """
        Unmute all pulse audio input sinks.
    """
    global muted_sinks
    for sink in pulse.sink_input_list():
        if sink.index in muted_sinks:
            pulse.sink_input_mute(sink.index, 0)
    muted_sinks = []


def pulse_lower_volume():
    """
        Lower volume of all pulse audio input sinks except the one named
        'mycroft-voice'.
    """
    for sink in pulse.sink_input_list():
        if sink.name != 'mycroft-voice':
            v = sink.volume
            v.value_flat *= 0.3
            pulse.volume_set(sink, v)


def pulse_restore_volume():
    """
        Restore volume of all pulse audio input sinks except the one named
        'mycroft-voice'.
    """
    for sink in pulse.sink_input_list():
        if sink.name != 'mycroft-voice':
            v = sink.volume
            v.value_flat /= 0.3
            pulse.volume_set(sink, v)


def _restore_volume(message):
    """
        Is triggered when mycroft is done speaking and restores the volume

        Args:
            message: message bus message, not used but required
    """
    global current
    global volume_is_low
    LOG.info('maybe restoring volume')
    if current:
        volume_is_low = False
        time.sleep(2)
        if not volume_is_low:
            LOG.info('restoring volume')
            current.restore_volume()
    if pulse_restore:
        pulse_restore()


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
    global service
    LOG.info('play')
    _stop()
    uri_type = tracks[0].split(':')[0]
    LOG.info('uri_type: ' + uri_type)
    # check if user requested a particular service
    if prefered_service and uri_type in prefered_service.supported_uris():
        selected_service = prefered_service
    # check if default supports the uri
    elif default and uri_type in default.supported_uris():
        LOG.info("Using default backend")
        LOG.info(default.name)
        selected_service = default
    else:  # Check if any other service can play the media
        LOG.info("Searching the services")
        for s in service:
            LOG.info(str(s))
            if uri_type in s.supported_uris():
                LOG.info("Service "+str(s)+" supports URI "+uri_type)
                selected_service = s
                break
        else:
            LOG.info('No service found for uri_type: ' + uri_type)
            return
    LOG.info('Clear list')
    selected_service.clear_list()
    LOG.info('Add tracks' + str(tracks))
    selected_service.add_list(tracks)
    LOG.info('Playing')
    selected_service.play()
    current = selected_service


def _play(message):
    """
        Handler for mycroft.audio.service.play. Starts playback of a
        tracklist. Also  determines if the user requested a special service.

        Args:
            message: message bus message, not used but required
    """
    global service
    LOG.info('mycroft.audio.service.play')
    LOG.info(message.data['tracks'])

    tracks = message.data['tracks']

    # Find if the user wants to use a specific backend
    for s in service:
        LOG.info(s.name)
        if s.name in message.data['utterance']:
            prefered_service = s
            LOG.info(s.name + ' would be prefered')
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
        track_info = current.track_info()
    else:
        track_info = {}
    ws.emit(Message('mycroft.audio.service.track_info_reply',
                    data=track_info))


def setup_pulseaudio_handlers(pulse_choice=None):
    """
        Select functions for handling lower volume/restore of
        pulse audio input sinks.

        Args:
            pulse_choice: method selection, can be eithe 'mute' or 'lower'
    """
    global pulse, pulse_quiet, pulse_restore

    if pulsectl and pulse_choice is not None:
        pulse = pulsectl.Pulse('Mycroft-audio-service')
        if pulse_choice == 'mute':
            pulse_quiet = pulse_mute
            pulse_restore = pulse_unmute
        elif pulse_choice == 'lower':
            pulse_quiet = pulse_lower_volume
            pulse_restore = pulse_restore_volume


def connect():
    global ws
    ws.run_forever()


def main():
    global ws
    global config
    ws = WebsocketClient()
    Configuration.init(ws)
    config = Configuration.get()
    speech.init(ws)

    # Setup control of pulse audio
    setup_pulseaudio_handlers(config.get('Audio').get('pulseaudio'))

    def echo(message):
        try:
            _message = json.loads(message)
            if 'mycroft.audio.service' not in _message.get('type'):
                return
            message = json.dumps(_message)
        except:
            pass
        LOG.debug(message)

    LOG.info("Staring Audio Services")
    ws.on('message', echo)
    ws.once('open', load_services_callback)
    try:
        ws.run_forever()
    except KeyboardInterrupt, e:
        LOG.exception(e)
        speech.shutdown()
        sys.exit()


if __name__ == "__main__":
    main()
