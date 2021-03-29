# Copyright 2019 Mycroft AI Inc.
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
"""Define the enclosure interface for Mark II devices."""
import json
import time
from threading import Timer
from websocket import WebSocketApp

from mycroft.client.enclosure.base import Enclosure
from mycroft.messagebus.message import Message
from mycroft.util import create_daemon, connected
from mycroft.util.log import LOG
from mycroft.enclosure.hardware_enclosure import HardwareEnclosure
from mycroft.util.hardware_capabilities import EnclosureCapabilities

import threading


class temperatureMonitorThread(threading.Thread):
    def __init__(self, fan_obj, led_obj, pal_obj):
        self.fan_obj = fan_obj
        self.led_obj = led_obj
        self.pal_obj = pal_obj
        self.exit_flag = False
        threading.Thread.__init__(self)

    def run(self):
        LOG.debug("temperature monitor thread started")
        while not self.exit_flag:
            time.sleep(60)

            LOG.info("CPU temperature is %s" % (self.fan_obj.get_cpu_temp(),))

            # TODO make this ratiometric
            current_temperature = self.fan_obj.get_cpu_temp()
            if current_temperature < 50.0:
                # anything below 122F we are fine
                self.fan_obj.set_fan_speed(0)
                LOG.debug("Fan turned off")
                self.led_obj._set_led(10, self.pal_obj.BLUE)
                continue

            if current_temperature > 50.0 and current_temperature < 60.0:
                # 122 - 140F we run fan at 25%
                self.fan_obj.set_fan_speed(25)
                LOG.debug("Fan set to 25%")
                self.led_obj._set_led(10, self.pal_obj.MAGENTA)
                continue

            if current_temperature > 60.0 and current_temperature <= 70.0:
                # 140 - 160F we run fan at 50%
                self.fan_obj.set_fan_speed(50)
                LOG.debug("Fan set to 50%")
                self.led_obj._set_led(10, self.pal_obj.BURNT_ORANGE)
                continue

            if current_temperature > 70.0:
                # > 160F we run fan at 100%
                self.fan_obj.set_fan_speed(100)
                LOG.debug("Fan set to 100%")
                self.led_obj._set_led(10, self.pal_obj.RED)
                continue


class pulseLedThread(threading.Thread):
    def __init__(self, led_obj, pal_obj):
        self.led_obj = led_obj
        self.pal_obj = pal_obj
        self.exit_flag = False
        self.color_tup = self.pal_obj.MYCROFT_GREEN
        self.delay = 0.1
        self.brightness = 100
        self.step_size = 5
        threading.Thread.__init__(self)

    def run(self):
        LOG.debug("pulse thread started")
        self.tmp_leds = []
        for x in range(0,10):
            self.tmp_leds.append( self.color_tup )

        self.led_obj.brightness = self.brightness / 100
        self.led_obj.set_leds( self.tmp_leds )

        while not self.exit_flag:

            if (self.brightness + self.step_size) > 100:
                self.brightness = self.brightness - self.step_size
                self.step_size = self.step_size * -1

            elif (self.brightness + self.step_size) < 0:
                self.brightness = self.brightness - self.step_size
                self.step_size = self.step_size * -1

            else:
                self.brightness += self.step_size

            self.led_obj.brightness = self.brightness / 100
            self.led_obj.set_leds( self.tmp_leds )

            time.sleep(self.delay)

        LOG.debug("pulse thread stopped")
        self.led_obj.brightness = 1.0
        self.led_obj.fill( self.pal_obj.BLACK )


class chaseLedThread(threading.Thread):
    def __init__(self, led_obj, background_color, foreground_color):
        self.led_obj = led_obj
        self.bkgnd_col = background_color
        self.fgnd_col = foreground_color
        self.exit_flag = False
        self.color_tup = foreground_color
        self.delay = 0.1
        tmp_leds = []
        for indx in range(0,10):
            tmp_leds.append(self.bkgnd_col)

        self.led_obj.set_leds(tmp_leds)
        threading.Thread.__init__(self)

    def run(self):
        LOG.debug("chase thread started")
        chase_ctr = 0
        while not self.exit_flag:
            chase_ctr += 1
            LOG.error("chase thread %s" % (chase_ctr,))
            for x in range(0,10):
                self.led_obj.set_led(x, self.fgnd_col)
                time.sleep(self.delay)
                self.led_obj.set_led(x, self.bkgnd_col)
            if chase_ctr > 10:
                self.exit_flag = True

        LOG.debug("chase thread stopped")
        self.led_obj.fill( (0,0,0) )


class EnclosureMark2(Enclosure):
    def __init__(self):
        LOG.info('** Initialize EnclosureMark2 **')
        super().__init__()
        self.display_bus_client = None
        self._define_event_handlers()
        self.finished_loading = False
        self.active_screen = 'loading'
        self.paused_screen = None
        self.is_pairing = False
        self.active_until_stopped = None
        self.reserved_led = 10
        self.mute_led = 11
        self.chaseLedThread = None
        self.pulseLedThread = None

        self.system_volume = 0.5   # pulse audio master system volume
        # if you want to do anything with the system volume
        # (ala pulseaudio, etc) do it here!
        self.current_volume = 0.5  # hardware/board level volume

        # TODO these need to come from a config value
        self.m2enc = HardwareEnclosure("Mark2", "sj201r4")
        self.m2enc.client_volume_handler = self.async_volume_handler

        # start the temperature monitor thread
        self.temperatureMonitorThread = temperatureMonitorThread(self.m2enc.fan, self.m2enc.leds, self.m2enc.palette)
        self.temperatureMonitorThread.start()

        self.m2enc.leds.set_leds([
                self.m2enc.palette.BLACK,
                self.m2enc.palette.BLACK,
                self.m2enc.palette.BLACK,
                self.m2enc.palette.BLACK,
                self.m2enc.palette.BLACK,
                self.m2enc.palette.BLACK,
                self.m2enc.palette.BLACK,
                self.m2enc.palette.BLACK,
                self.m2enc.palette.BLACK,
                self.m2enc.palette.BLACK
                ])

        self.m2enc.leds._set_led_with_brightness(
            self.reserved_led,
            self.m2enc.palette.MAGENTA,
            0.5)

        # set mute led based on reality
        mute_led_color = self.m2enc.palette.GREEN
        if self.m2enc.switches.SW_MUTE == 1:
            mute_led_color = self.m2enc.palette.RED

        self.m2enc.leds._set_led_with_brightness(
            self.mute_led,
            mute_led_color,
            1.0)

        self.default_caps = EnclosureCapabilities()

        LOG.info('** EnclosureMark2 initalized **')
        self.bus.once('mycroft.skills.trained', self.is_device_ready)


    def is_device_ready(self, message):
        is_ready = False
        # Bus service assumed to be alive if messages sent and received
        # Enclosure assumed to be alive if this method is running
        services = {'audio': False, 'speech': False, 'skills': False}
        start = time.monotonic()
        while not is_ready:
            is_ready = self.check_services_ready(services)
            if is_ready:
                break
            elif time.monotonic() - start >= 60:
                raise Exception('Timeout waiting for services start.')
            else:
                time.sleep(3)

        if is_ready:
            LOG.info("All Mycroft Services have reported ready.")
            if connected():
                self.bus.emit(Message('mycroft.ready'))
            else:
                self.bus.emit(Message('mycroft.wifi.setup'))

        return is_ready

    def check_services_ready(self, services):
        """Report if all specified services are ready.

        services (iterable): service names to check.
        """
        for ser in services:
            services[ser] = False
            response = self.bus.wait_for_response(Message(
                'mycroft.{}.is_ready'.format(ser)))
            if response and response.data['status']:
                services[ser] = True
        return all([services[ser] for ser in services])

    def async_volume_handler(self, vol):
        LOG.error("ASYNC SET VOL PASSED IN %s" % (vol,))
        if vol > 1.0:
            vol = vol / 10
        self.current_volume = vol
        LOG.error("ASYNC SET VOL TO %s" % (self.current_volume,))
        # notify anybody listening on the bus who cares
        self.bus.emit(Message("hardware.volume", {
            "volume": self.current_volume}, context={"source": ["enclosure"]}))

    def _define_event_handlers(self):
        """Assign methods to act upon message bus events."""
        self.bus.on('mycroft.volume.set', self.on_volume_set)
        self.bus.on('mycroft.volume.get', self.on_volume_get)
        self.bus.on('mycroft.volume.duck', self.on_volume_duck)
        self.bus.on('mycroft.volume.unduck', self.on_volume_unduck)
        self.bus.on('recognizer_loop:record_begin', self.handle_start_recording)
        self.bus.on('recognizer_loop:record_end', self.handle_stop_recording)
        self.bus.on('recognizer_loop:audio_output_end', self.handle_end_audio)
        self.bus.on('mycroft.speech.recognition.unknown', self.handle_end_audio)
        self.bus.on('mycroft.stop.handled', self.handle_end_audio)
        self.bus.on('mycroft.capabilities.get', self.on_capabilities_get)

    def handle_start_recording(self, message):
        LOG.debug("Gathering speech stuff")
        if self.pulseLedThread is None:
            self.pulseLedThread = pulseLedThread(self.m2enc.leds, self.m2enc.palette)
            self.pulseLedThread.start()

    def handle_stop_recording(self, message):
        background_color = self.m2enc.palette.BLUE
        foreground_color = self.m2enc.palette.BLACK
        LOG.debug("Got spoken stuff")
        if self.pulseLedThread is not None:
            self.pulseLedThread.exit_flag = True
            self.pulseLedThread.join()
            self.pulseLedThread = None
        if self.chaseLedThread is None:
            self.chaseLedThread = chaseLedThread(self.m2enc.leds, background_color, foreground_color)
            self.chaseLedThread.start()

    def handle_end_audio(self, message):
        LOG.debug("Finished playing audio")
        if self.chaseLedThread is not None:
            self.chaseLedThread.exit_flag = True
            self.chaseLedThread.join()
            self.chaseLedThread = None

    def on_volume_duck(self, message):
        # TODO duck it anyway using set vol
        LOG.warning("Mark2 volume duck deprecated! use volume set instead.")
        self.m2enc.hardware_volume.set_volume(float(0.1))  # TODO make configurable 'duck_vol'

    def on_volume_unduck(self, message):
        # TODO duck it anyway using set vol
        LOG.warning("Mark2 volume unduck deprecated! use volume set instead.")
        self.m2enc.hardware_volume.set_volume(float(self.current_volume))

    def on_volume_set(self, message):
        self.current_volume = message.data.get("percent", self.current_volume)
        LOG.info('Mark2:interface.py set volume to %s' %
                 (self.current_volume,))
        self.m2enc.hardware_volume.set_volume(float(self.current_volume))

        # notify anybody listening on the bus who cares
        self.bus.emit(Message("hardware.volume", {
            "volume": self.current_volume}, context={"source": ["enclosure"]}))

    def on_volume_get(self, message):
        self.current_volume = self.m2enc.hardware_volume.get_volume()

        if self.current_volume > 1.0:
            self.current_volume = self.current_volume / 10

        LOG.info('Mark2:interface.py get and emit volume %s' %
                 (self.current_volume,))
        self.bus.emit(
            message.response(
                data={'percent': self.current_volume, 'muted': False}))

    def on_capabilities_get(self, message):
        LOG.info('Mark2:interface.py get capabilities requested')

        self.bus.emit(
            message.response(
                data={
                    'default': self.default_caps.caps, 
                    'extra': self.m2enc.capabilities,
                    'board_type': self.m2enc.board_type,
                    'leds': self.m2enc.leds.capabilities,
                    'volume': self.m2enc.hardware_volume.capabilities,
                    'switches': self.m2enc.switches.capabilities
                    }
                ))

    def terminate(self):
        self.m2enc.leds._set_led(10, (0, 0, 0))  # blank out reserved led
        self.m2enc.leds._set_led(11, (0, 0, 0))  # BUG set to real value!
        self.m2enc.terminate()
