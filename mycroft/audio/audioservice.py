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

import importlib
import sys
import time
from os import listdir
from os.path import abspath, dirname, basename, isdir, join
from threading import Lock

from mycroft.audio.services import RemoteAudioBackend
from mycroft.configuration import Configuration
from mycroft.messagebus.message import Message
from mycroft.util.log import LOG
from mycroft.util.monotonic_event import MonotonicEvent
from mycroft.util.plugins import find_plugins

MINUTES = 60  # Seconds in a minute

MAINMODULE = '__init__'
sys.path.append(abspath(dirname(__file__)))


def create_service_spec(service_folder):
    """Prepares a descriptor that can be used together with imp.

        Args:
            service_folder: folder that shall be imported.

        Returns:
            Dict with import information
    """
    module_name = 'audioservice_' + basename(service_folder)
    path = join(service_folder, MAINMODULE + '.py')
    spec = importlib.util.spec_from_file_location(module_name, path)
    mod = importlib.util.module_from_spec(spec)
    info = {'spec': spec, 'mod': mod, 'module_name': module_name}
    return {"name": basename(service_folder), "info": info}


def get_services(services_folder):
    """
        Load and initialize services from all subfolders.

        Args:
            services_folder: base folder to look for services in.

        Returns:
            Sorted list of audio services.
    """
    LOG.info("Loading services from " + services_folder)
    services = []
    possible_services = listdir(services_folder)
    for i in possible_services:
        location = join(services_folder, i)
        if (isdir(location) and
                not MAINMODULE + ".py" in listdir(location)):
            for j in listdir(location):
                name = join(location, j)
                if (not isdir(name) or
                        not MAINMODULE + ".py" in listdir(name)):
                    continue
                try:
                    services.append(create_service_spec(name))
                except Exception:
                    LOG.error('Failed to create service from ' + name,
                              exc_info=True)
        if (not isdir(location) or
                not MAINMODULE + ".py" in listdir(location)):
            continue
        try:
            services.append(create_service_spec(location))
        except Exception:
            LOG.error('Failed to create service from ' + location,
                      exc_info=True)
    return sorted(services, key=lambda p: p.get('name'))


def setup_service(service_module, config, bus):
    """Run the appropriate setup function and return created service objects.

    Args:
        service_module: Python module to run
        config (dict): Mycroft configuration dict
        bus (MessageBusClient): Messagebus interface

    Returns:
        (list) List of created services.
    """
    if (hasattr(service_module, 'autodetect') and
            callable(service_module.autodetect)):
        try:
            return service_module.autodetect(config, bus)
        except Exception as e:
            LOG.error('Failed to autodetect. ' + repr(e))
    elif hasattr(service_module, 'load_service'):
        try:
            return service_module.load_service(config, bus)
        except Exception as e:
            LOG.error('Failed to load service. ' + repr(e))
    else:
        LOG.error('Failed to load service. loading function not found')
        return None


def load_internal_services(config, bus, path=None):
    """Load audio services included in Mycroft-core.

    Args:
        config: configuration dict for the audio backends.
        bus: Mycroft messagebus
        path: (default None) optional path for builtin audio service
              implementations

    Returns:
        List of started services
    """
    if path is None:
        path = dirname(abspath(__file__)) + '/services/'
    service_directories = get_services(path)
    service = []
    for descriptor in service_directories:
        try:
            service_module = descriptor['info']['mod']
            spec = descriptor['info']['spec']
            module_name = descriptor['info']['module_name']
            sys.modules[module_name] = service_module
            spec.loader.exec_module(service_module)
        except Exception as e:
            LOG.error('Failed to import module ' + descriptor['name'] + '\n' +
                      repr(e))
        else:
            s = setup_service(service_module, config, bus)
            if s:
                LOG.info('Loaded ' + descriptor['name'])
                service += s

    return service


def load_plugins(config, bus):
    """Load installed audioservice plugins.

    Args:
        config: configuration dict for the audio backends.
        bus: Mycroft messagebus

    Returns:
        List of started services
    """
    plugin_services = []
    found_plugins = find_plugins('mycroft.plugin.audioservice')
    for plugin_name, plugin_module in found_plugins.items():
        LOG.info(f'Loading audio service plugin: {plugin_name}')
        service = setup_service(plugin_module, config, bus)
        if service:
            plugin_services += service
    return plugin_services


def load_services(config, bus, path=None):
    """Load builtin services as well as service plugins

    The builtin service folder is scanned (or a folder indicated by the path
    parameter) for services and plugins registered with the
    "mycroft.plugin.audioservice" entrypoint group.

    Args:
        config: configuration dict for the audio backends.
        bus: Mycroft messagebus
        path: (default None) optional path for builtin audio service
              implementations

    Returns:
        List of started services.
    """
    return (load_internal_services(config, bus, path) +
            load_plugins(config, bus))


class AudioService:
    """ Audio Service class.
        Handles playback of audio and selecting proper backend for the uri
        to be played.
    """

    def __init__(self, bus):
        """
            Args:
                bus: Mycroft messagebus
        """
        self.bus = bus
        self.config = Configuration.get().get("Audio")
        self.service_lock = Lock()

        self.default = None
        self.service = []
        self.current = None
        self.play_start_time = 0
        self.volume_is_low = False

        self._loaded = MonotonicEvent()
        self.load_services()

    def load_services(self):
        """Method for loading services.

        Sets up the global service, default and registers the event handlers
        for the subsystem.
        """
        services = load_services(self.config, self.bus)
        # Sort services so local services are checked first
        local = [s for s in services if not isinstance(s, RemoteAudioBackend)]
        remote = [s for s in services if isinstance(s, RemoteAudioBackend)]
        self.service = local + remote

        # Register end of track callback
        for s in self.service:
            s.set_track_start_callback(self.track_start)

        # Find default backend
        default_name = self.config.get('default-backend', '')
        LOG.info('Finding default backend...')
        for s in self.service:
            if s.name == default_name:
                self.default = s
                LOG.info('Found ' + self.default.name)
                break
        else:
            self.default = None
            LOG.info('no default found')

        # Setup event handlers
        self.bus.on('mycroft.audio.service.play', self._play)
        self.bus.on('mycroft.audio.service.queue', self._queue)
        self.bus.on('mycroft.audio.service.pause', self._pause)
        self.bus.on('mycroft.audio.service.resume', self._resume)
        self.bus.on('mycroft.audio.service.stop', self._stop)
        self.bus.on('mycroft.audio.service.next', self._next)
        self.bus.on('mycroft.audio.service.prev', self._prev)
        self.bus.on('mycroft.audio.service.track_info', self._track_info)
        self.bus.on('mycroft.audio.service.list_backends', self._list_backends)
        self.bus.on('mycroft.audio.service.set_track_position',
                    self._set_track_position)
        self.bus.on('mycroft.audio.service.get_track_position',
                    self._get_track_position)
        self.bus.on('mycroft.audio.service.get_track_length',
                    self._get_track_length)
        self.bus.on('mycroft.audio.service.seek_forward', self._seek_forward)
        self.bus.on('mycroft.audio.service.seek_backward', self._seek_backward)
        self.bus.on('recognizer_loop:audio_output_start', self._lower_volume)
        self.bus.on('recognizer_loop:record_begin', self._lower_volume)
        self.bus.on('recognizer_loop:audio_output_end', self._restore_volume)
        self.bus.on('recognizer_loop:record_end',
                    self._restore_volume_after_record)

        self._loaded.set()  # Report services loaded

    def wait_for_load(self, timeout=3 * MINUTES):
        """Wait for services to be loaded.

        Args:
            timeout (float): Seconds to wait (default 3 minutes)
        Returns:
            (bool) True if loading completed within timeout, else False.
        """
        return self._loaded.wait(timeout)

    def track_start(self, track):
        """Callback method called from the services to indicate start of
        playback of a track or end of playlist.
        """
        if track:
            # Inform about the track about to start.
            LOG.debug('New track coming up!')
            self.bus.emit(Message('mycroft.audio.playing_track',
                                  data={'track': track}))
        else:
            # If no track is about to start last track of the queue has been
            # played.
            LOG.debug('End of playlist!')
            self.bus.emit(Message('mycroft.audio.queue_end'))

    def _pause(self, message=None):
        """
            Handler for mycroft.audio.service.pause. Pauses the current audio
            service.

            Args:
                message: message bus message, not used but required
        """
        if not self._is_message_for_service(message):
            return
        if self.current:
            self.current.pause()

    def _resume(self, message=None):
        """
            Handler for mycroft.audio.service.resume.

            Args:
                message: message bus message, not used but required
        """
        if not self._is_message_for_service(message):
            return
        if self.current:
            self.current.resume()

    def _next(self, message=None):
        """
            Handler for mycroft.audio.service.next. Skips current track and
            starts playing the next.

            Args:
                message: message bus message, not used but required
        """
        if not self._is_message_for_service(message):
            return
        if self.current:
            self.current.next()

    def _prev(self, message=None):
        """
            Handler for mycroft.audio.service.prev. Starts playing the previous
            track.

            Args:
                message: message bus message, not used but required
        """
        if not self._is_message_for_service(message):
            return
        if self.current:
            self.current.previous()

    def _perform_stop(self, message=None):
        """Stop audioservice if active."""
        if not self._is_message_for_service(message):
            return
        if self.current:
            name = self.current.name
            if self.current.stop():
                if message:
                    msg = message.reply("mycroft.stop.handled",
                                        {"by": "audio:" + name})
                else:
                    msg = Message("mycroft.stop.handled",
                                  {"by": "audio:" + name})
                self.bus.emit(msg)

        self.current = None

    def _stop(self, message=None):
        """
            Handler for mycroft.stop. Stops any playing service.

            Args:
                message: message bus message, not used but required
        """
        if not self._is_message_for_service(message):
            return
        if time.monotonic() - self.play_start_time > 1:
            LOG.debug('stopping all playing services')
            with self.service_lock:
                try:
                    self._perform_stop(message)
                except Exception as e:
                    LOG.exception(e)
                    LOG.error("failed to stop!")
        LOG.info('END Stop')

    def _lower_volume(self, message=None):
        """
            Is triggered when mycroft starts to speak and reduces the volume.

            Args:
                message: message bus message, not used but required
        """
        if not self._is_message_for_service(message):
            return
        if self.current:
            LOG.debug('lowering volume')
            self.current.lower_volume()
            self.volume_is_low = True

    def _restore_volume(self, message=None):
        """Triggered when mycroft is done speaking and restores the volume."""
        if not self._is_message_for_service(message):
            return
        current = self.current
        if current:
            LOG.debug('restoring volume')
            self.volume_is_low = False
            current.restore_volume()

    def _restore_volume_after_record(self, message=None):
        """
            Restores the volume when Mycroft is done recording.
            If no utterance detected, restore immediately.
            If no response is made in reasonable time, then also restore.

            Args:
                message: message bus message, not used but required
        """
        if not self._is_message_for_service(message):
            return

        def restore_volume():
            LOG.debug('restoring volume')
            self.current.restore_volume()

        if self.current:
            self.bus.on('recognizer_loop:speech.recognition.unknown',
                        restore_volume)
            speak_msg_detected = self.bus.wait_for_message('speak',
                                                           timeout=8.0)
            if not speak_msg_detected:
                restore_volume()
            self.bus.remove('recognizer_loop:speech.recognition.unknown',
                            restore_volume)
        else:
            LOG.debug("No audio service to restore volume of")

    def play(self, tracks, prefered_service, repeat=False):
        """
            play starts playing the audio on the prefered service if it
            supports the uri. If not the next best backend is found.

            Args:
                tracks: list of tracks to play.
                repeat: should the playlist repeat
                prefered_service: indecates the service the user prefer to play
                                  the tracks.
        """
        self._perform_stop()

        if isinstance(tracks[0], str):
            uri_type = tracks[0].split(':')[0]
        else:
            uri_type = tracks[0][0].split(':')[0]

        # check if user requested a particular service
        if prefered_service and uri_type in prefered_service.supported_uris():
            selected_service = prefered_service
        # check if default supports the uri
        elif self.default and uri_type in self.default.supported_uris():
            LOG.debug("Using default backend ({})".format(self.default.name))
            selected_service = self.default
        else:  # Check if any other service can play the media
            LOG.debug("Searching the services")
            for s in self.service:
                if uri_type in s.supported_uris():
                    LOG.debug("Service {} supports URI {}".format(s, uri_type))
                    selected_service = s
                    break
            else:
                LOG.info('No service found for uri_type: ' + uri_type)
                return
        if not selected_service.supports_mime_hints:
            tracks = [t[0] if isinstance(t, list) else t for t in tracks]
        selected_service.clear_list()
        selected_service.add_list(tracks)
        selected_service.play(repeat)
        self.current = selected_service
        self.play_start_time = time.monotonic()

    @staticmethod
    def _is_message_for_service(message):
        if not message:
            return True
        destination = message.context.get("destination")
        if destination:
            if "audio" in destination or "debug_cli" in destination:
                # request from device
                return True
            # external request, do not handle
            return False
        # broadcast for everyone
        return True

    def _queue(self, message):
        if not self._is_message_for_service(message):
            return
        if self.current:
            with self.service_lock:
                try:
                    tracks = message.data['tracks']
                    self.current.add_list(tracks)
                except Exception as e:
                    LOG.exception(e)
                    LOG.error("failed to queue tracks!")
        else:
            self._play(message)

    def _play(self, message):
        """
            Handler for mycroft.audio.service.play. Starts playback of a
            tracklist. Also  determines if the user requested a special
            service.

            Args:
                message: message bus message, not used but required
        """
        if not self._is_message_for_service(message):
            return
        with self.service_lock:
            tracks = message.data['tracks']
            repeat = message.data.get('repeat', False)
            # Find if the user wants to use a specific backend
            for s in self.service:
                try:
                    if ('utterance' in message.data and
                            s.name in message.data['utterance']):
                        prefered_service = s
                        LOG.debug(s.name + ' would be prefered')
                        break
                except Exception as e:
                    LOG.error(f"failed to parse audio service name: {s}")
            else:
                prefered_service = None
            try:
                self.play(tracks, prefered_service, repeat)
                time.sleep(0.5)
            except Exception as e:
                LOG.exception(e)

    def _track_info(self, message):
        """
            Returns track info on the message bus.

            Args:
                message: message bus message, not used but required
        """
        if not self._is_message_for_service(message):
            return
        if self.current:
            track_info = self.current.track_info()
        else:
            track_info = {}
        self.bus.emit(message.reply('mycroft.audio.service.track_info_reply',
                                    data=track_info))

    def _list_backends(self, message):
        """ Return a dict of available backends. """
        if not self._is_message_for_service(message):
            return
        data = {}
        for s in self.service:
            info = {
                'supported_uris': s.supported_uris(),
                'default': s == self.default,
                'remote': isinstance(s, RemoteAudioBackend)
            }
            data[s.name] = info
        self.bus.emit(message.response(data))

    def _get_track_length(self, message):
        """
        getting the duration of the audio in milliseconds
        """
        if not self._is_message_for_service(message):
            return
        dur = None
        if self.current:
            dur = self.current.get_track_length()
        self.bus.emit(message.response({"length": dur}))

    def _get_track_position(self, message):
        """
        get current position in milliseconds
        """
        if not self._is_message_for_service(message):
            return
        pos = None
        if self.current:
            pos = self.current.get_track_position()
        self.bus.emit(message.response({"position": pos}))

    def _set_track_position(self, message):
        """
            Handle message bus command to go to position (in milliseconds)

            Args:
                message: message bus message
        """
        if not self._is_message_for_service(message):
            return
        milliseconds = message.data.get("position")
        if milliseconds and self.current:
            self.current.set_track_position(milliseconds)

    def _seek_forward(self, message):
        """
            Handle message bus command to skip X seconds

            Args:
                message: message bus message
        """
        if not self._is_message_for_service(message):
            return
        seconds = message.data.get("seconds", 1)
        if self.current:
            self.current.seek_forward(seconds)

    def _seek_backward(self, message):
        """
            Handle message bus command to rewind X seconds

            Args:
                message: message bus message
        """
        if not self._is_message_for_service(message):
            return
        seconds = message.data.get("seconds", 1)
        if self.current:
            self.current.seek_backward(seconds)

    def shutdown(self):
        for s in self.service:
            try:
                LOG.info('shutting down ' + s.name)
                s.shutdown()
            except Exception as e:
                LOG.error('shutdown of ' + s.name + ' failed: ' + repr(e))

        # remove listeners
        self.bus.remove('mycroft.audio.service.play', self._play)
        self.bus.remove('mycroft.audio.service.queue', self._queue)
        self.bus.remove('mycroft.audio.service.pause', self._pause)
        self.bus.remove('mycroft.audio.service.resume', self._resume)
        self.bus.remove('mycroft.audio.service.stop', self._stop)
        self.bus.remove('mycroft.audio.service.next', self._next)
        self.bus.remove('mycroft.audio.service.prev', self._prev)
        self.bus.remove('mycroft.audio.service.track_info', self._track_info)
        self.bus.remove('mycroft.audio.service.get_track_position',
                        self._get_track_position)
        self.bus.remove('mycroft.audio.service.set_track_position',
                        self._set_track_position)
        self.bus.remove('mycroft.audio.service.get_track_length',
                        self._get_track_length)
        self.bus.remove('mycroft.audio.service.seek_forward',
                        self._seek_forward)
        self.bus.remove('mycroft.audio.service.seek_backward',
                        self._seek_backward)
        self.bus.remove('recognizer_loop:audio_output_start',
                        self._lower_volume)
        self.bus.remove('recognizer_loop:record_begin', self._lower_volume)
        self.bus.remove('recognizer_loop:audio_output_end',
                        self._restore_volume)
        self.bus.remove('recognizer_loop:record_end',
                        self._restore_volume_after_record)
