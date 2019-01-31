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

import imp
import sys
import time
from os import listdir
from os.path import abspath, dirname, basename, isdir, join
from threading import Lock

from mycroft.configuration import Configuration
from mycroft.messagebus.message import Message
from mycroft.util.log import LOG

from .services import RemoteAudioBackend

try:
    import pulsectl
except ImportError:
    pulsectl = None

MAINMODULE = '__init__'
sys.path.append(abspath(dirname(__file__)))


def create_service_descriptor(service_folder):
    """Prepares a descriptor that can be used together with imp.

        Args:
            service_folder: folder that shall be imported.

        Returns:
            Dict with import information
    """
    info = imp.find_module(MAINMODULE, [service_folder])
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
                    services.append(create_service_descriptor(name))
                except Exception:
                    LOG.error('Failed to create service from ' + name,
                              exc_info=True)
        if (not isdir(location) or
                not MAINMODULE + ".py" in listdir(location)):
            continue
        try:
            services.append(create_service_descriptor(location))
        except Exception:
            LOG.error('Failed to create service from ' + location,
                      exc_info=True)
    return sorted(services, key=lambda p: p.get('name'))


def load_services(config, bus, path=None):
    """
        Search though the service directory and load any services.

        Args:
            config: configuration dict for the audio backends.
            bus: Mycroft messagebus

        Returns:
            List of started services.
    """
    if path is None:
        path = dirname(abspath(__file__)) + '/services/'
    service_directories = get_services(path)
    service = []
    for descriptor in service_directories:
        LOG.info('Loading ' + descriptor['name'])
        try:
            service_module = imp.load_module(descriptor["name"] + MAINMODULE,
                                             *descriptor["info"])
        except Exception as e:
            LOG.error('Failed to import module ' + descriptor['name'] + '\n' +
                      repr(e))
            continue

        if (hasattr(service_module, 'autodetect') and
                callable(service_module.autodetect)):
            try:
                s = service_module.autodetect(config, bus)
                service += s
            except Exception as e:
                LOG.error('Failed to autodetect. ' + repr(e))
        if hasattr(service_module, 'load_service'):
            try:
                s = service_module.load_service(config, bus)
                service += s
            except Exception as e:
                LOG.error('Failed to load service. ' + repr(e))

    return service


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
        self.pulse = None
        self.pulse_quiet = None
        self.pulse_restore = None

        self.muted_sinks = []
        # Setup control of pulse audio
        self.setup_pulseaudio_handlers(self.config.get('pulseaudio'))
        bus.once('open', self.load_services_callback)

    def load_services_callback(self):
        """
            Main callback function for loading services. Sets up the globals
            service and default and registers the event handlers for the
            subsystem.
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
        self.bus.on('mycroft.audio.service.seek_forward', self._seek_forward)
        self.bus.on('mycroft.audio.service.seek_backward', self._seek_backward)
        self.bus.on('recognizer_loop:audio_output_start', self._lower_volume)
        self.bus.on('recognizer_loop:record_begin', self._lower_volume)
        self.bus.on('recognizer_loop:audio_output_end', self._restore_volume)
        self.bus.on('recognizer_loop:record_end', self._restore_volume)

    def track_start(self, track):
        """
            Callback method called from the services to indicate start of
            playback of a track.
        """
        self.bus.emit(Message('mycroft.audio.playing_track',
                              data={'track': track}))

    def _pause(self, message=None):
        """
            Handler for mycroft.audio.service.pause. Pauses the current audio
            service.

            Args:
                message: message bus message, not used but required
        """
        if self.current:
            self.current.pause()

    def _resume(self, message=None):
        """
            Handler for mycroft.audio.service.resume.

            Args:
                message: message bus message, not used but required
        """
        if self.current:
            self.current.resume()

    def _next(self, message=None):
        """
            Handler for mycroft.audio.service.next. Skips current track and
            starts playing the next.

            Args:
                message: message bus message, not used but required
        """
        if self.current:
            self.current.next()

    def _prev(self, message=None):
        """
            Handler for mycroft.audio.service.prev. Starts playing the previous
            track.

            Args:
                message: message bus message, not used but required
        """
        if self.current:
            self.current.previous()

    def _stop(self, message=None):
        """
            Handler for mycroft.stop. Stops any playing service.

            Args:
                message: message bus message, not used but required
        """
        if time.monotonic() - self.play_start_time > 1:
            LOG.debug('stopping all playing services')
            with self.service_lock:
                if self.current:
                    name = self.current.name
                    if self.current.stop():
                        self.bus.emit(Message("mycroft.stop.handled",
                                              {"by": "audio:" + name}))

                    self.current = None

    def _lower_volume(self, message=None):
        """
            Is triggered when mycroft starts to speak and reduces the volume.

            Args:
                message: message bus message, not used but required
        """
        if self.current:
            LOG.debug('lowering volume')
            self.current.lower_volume()
            self.volume_is_low = True
        try:
            if self.pulse_quiet:
                self.pulse_quiet()
        except Exception as exc:
            LOG.error(exc)

    def pulse_mute(self):
        """
            Mute all pulse audio input sinks except for the one named
            'mycroft-voice'.
        """
        for sink in self.pulse.sink_input_list():
            if sink.name != 'mycroft-voice':
                self.pulse.sink_input_mute(sink.index, 1)
                self.muted_sinks.append(sink.index)

    def pulse_unmute(self):
        """
            Unmute all pulse audio input sinks.
        """
        for sink in self.pulse.sink_input_list():
            if sink.index in self.muted_sinks:
                self.pulse.sink_input_mute(sink.index, 0)
        self.muted_sinks = []

    def pulse_lower_volume(self):
        """
            Lower volume of all pulse audio input sinks except the one named
            'mycroft-voice'.
        """
        for sink in self.pulse.sink_input_list():
            if sink.name != 'mycroft-voice':
                volume = sink.volume
                volume.value_flat *= 0.3
                self.pulse.volume_set(sink, volume)

    def pulse_restore_volume(self):
        """
            Restore volume of all pulse audio input sinks except the one named
            'mycroft-voice'.
        """
        for sink in self.pulse.sink_input_list():
            if sink.name != 'mycroft-voice':
                volume = sink.volume
                volume.value_flat /= 0.3
                self.pulse.volume_set(sink, volume)

    def _restore_volume(self, message):
        """
            Is triggered when mycroft is done speaking and restores the volume

            Args:
                message: message bus message, not used but required
        """
        if self.current:
            LOG.debug('restoring volume')
            self.volume_is_low = False
            time.sleep(2)
            if not self.volume_is_low:
                self.current.restore_volume()
        if self.pulse_restore:
            self.pulse_restore()

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
        self._stop()

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

    def _queue(self, message):
        if self.current:
            tracks = message.data['tracks']
            self.current.add_list(tracks)
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
        tracks = message.data['tracks']
        repeat = message.data.get('repeat', False)
        # Find if the user wants to use a specific backend
        for s in self.service:
            if ('utterance' in message.data and
                    s.name in message.data['utterance']):
                prefered_service = s
                LOG.debug(s.name + ' would be prefered')
                break
        else:
            prefered_service = None
        self.play(tracks, prefered_service, repeat)

    def _track_info(self, message):
        """
            Returns track info on the message bus.

            Args:
                message: message bus message, not used but required
        """
        if self.current:
            track_info = self.current.track_info()
        else:
            track_info = {}
        self.bus.emit(Message('mycroft.audio.service.track_info_reply',
                              data=track_info))

    def _seek_forward(self, message):
        """
            Handle message bus command to skip X seconds

            Args:
                message: message bus message
        """
        seconds = message.data.get("seconds", 1)
        if self.current:
            self.current.seek_forward(seconds)

    def _seek_backward(self, message):
        """
            Handle message bus command to rewind X seconds

            Args:
                message: message bus message
        """
        seconds = message.data.get("seconds", 1)
        if self.current:
            self.current.seek_backward(seconds)

    def setup_pulseaudio_handlers(self, pulse_choice=None):
        """
            Select functions for handling lower volume/restore of
            pulse audio input sinks.

            Args:
                pulse_choice: method selection, can be eithe 'mute' or 'lower'
        """
        if pulsectl and pulse_choice:
            self.pulse = pulsectl.Pulse('Mycroft-audio-service')
            if pulse_choice == 'mute':
                self.pulse_quiet = self.pulse_mute
                self.pulse_restore = self.pulse_unmute
            elif pulse_choice == 'lower':
                self.pulse_quiet = self.pulse_lower_volume
                self.pulse_restore = self.pulse_restore_volume

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
        self.bus.remove('mycroft.audio.service.seek_forward',
                        self._seek_forward)
        self.bus.remove('mycroft.audio.service.seek_backward',
                        self._seek_backward)
        self.bus.remove('recognizer_loop:audio_output_start',
                        self._lower_volume)
        self.bus.remove('recognizer_loop:record_begin', self._lower_volume)
        self.bus.remove('recognizer_loop:audio_output_end',
                        self._restore_volume)
        self.bus.remove('recognizer_loop:record_end', self._restore_volume)
        self.bus.remove('mycroft.stop', self._stop)
