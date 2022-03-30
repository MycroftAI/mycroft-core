#!/usr/bin/env python3
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
#
# File: neo_pixel_set_leds.py
#
# Description:
#   neo_pixel_set_leds.py is a less than ideal way to handle the
#   Mark2 LEDs but neopixel requires sudo and skills
#   don't run as root.
#
#   The Mark2 has 12 RGB LEDS. Each LED is represented by an
#   RGB tuple. So for example (255,0,0) would render red,
#   (0,0,255) would render blue, etc. Note this script
#   is a stateless command line utility.
#
# Usage:
#    sudo neo_pixel_set_leds.py 12_RGB_tuples
#
#    Note: 12 RGB tuples is really 36 space separated
#    values between 0-255
#
#    Also Note: the neo pixel leds require you to run
#               sudo pip3 install rpi_ws281x adafruit-circuitpython-neopixel
#               if you are not going to use neo pixels (instead you will use
#               xmos to control the leds) nothing additional is required.
#
import board
import neopixel
import sys

# process cmd line input
led_values = []
try:
    led_values = [int(x) for x in sys.argv[1:]]
except Exception:
    sys.exit(-1)  # ignore invalid input

it = iter(led_values)  # convert to iterator
led_tuple = zip(it, it, it)  # convert to tuples

num_leds = 12  # sj201 has 12 leds

pixels = neopixel.NeoPixel(
    board.D18,  # gpio pin
    num_leds,  # number of leds
    brightness=0.2,
    auto_write=False,  # wait for show()
    pixel_order=neopixel.GRB,  # pin order mapping
)

# fill pixels with command line input
for x in range(num_leds):
    pixels[x] = next(led_tuple)
pixels.show()

sys.exit(0)
