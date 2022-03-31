# Copyright 2020 Mycroft AI Inc.
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

# Mark2 current capabilities

from mycroft.configuration import Configuration


class Capabilities:
    capabilities = {
        "sj201r4": {
            "Led": {"name": "led_sj201r4", "type": "MycroftLed"},
            "Switch": {"name": "switch_gpio", "type": "MycroftSwitch"},
            "Volume": {"name": "volume_sj201r4", "type": "MycroftVolume"},
            "Fan": {"name": "fan_sj201r4", "type": "MycroftFan"},
            "Palette": {"name": "default_palette", "type": "MycroftPalette"},
        },
        "xmos_all": {
            "Led": {"name": "led_xmos_usb", "type": "MycroftLed"},
            "Switch": {"name": "switch_xmos_usb", "type": "MycroftSwitch"},
            "Volume": {"name": "volume_xmos_usb", "type": "MycroftVolume"},
            "Palette": {"name": "default_palette", "type": "MycroftPalette"},
        },
        "xmos_volume_gpio_switches_neo_pixel_leds": {
            "Led": {"name": "led_neo_pixel", "type": "MycroftLed"},
            "Switch": {"name": "switch_gpio", "type": "MycroftSwitch"},
            "Volume": {"name": "volume_xmos_usb", "type": "MycroftVolume"},
            "Palette": {"name": "default_palette", "type": "MycroftPalette"},
        },
        "i2c_volume_gpio_switches_neo_pixel_leds": {
            "Led": {"name": "led_neo_pixel", "type": "MycroftLed"},
            "Switch": {"name": "switch_gpio", "type": "MycroftSwitch"},
            "Volume": {"name": "volume_i2c", "type": "MycroftVolume"},
            "Palette": {"name": "default_palette", "type": "MycroftPalette"},
        },
        "xmos_volume_gpio_switches_xmos_leds": {
            "Led": {"name": "led_xmos_usb", "type": "MycroftLed"},
            "Switch": {"name": "switch_gpio", "type": "MycroftSwitch"},
            "Volume": {"name": "volume_xmos_usb", "type": "MycroftVolume"},
            "Palette": {"name": "default_palette", "type": "MycroftPalette"},
        },
        "dummy": {
            "Fan": {"name": "fan_dummy", "type": "MycroftFan"},
            "Led": {"name": "led_dummy", "type": "MycroftLed"},
            "Switch": {"name": "switch_dummy", "type": "MycroftSwitch"},
            "Volume": {"name": "volume_dummy", "type": "MycroftVolume"},
            "Palette": {"name": "default_palette", "type": "MycroftPalette"},
        },
    }

    default_board_type = "sj201r4"
