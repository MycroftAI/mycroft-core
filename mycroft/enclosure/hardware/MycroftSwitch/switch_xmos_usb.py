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

import threading
import subprocess
import time
from mycroft.enclosure.hardware.MycroftSwitch.MycroftSwitch import MycroftSwitch


class Switch(MycroftSwitch):
    sleep_time = 0.2
    # sudo_cmd = "sudo"
    sudo_cmd = ""
    gpi_read_cmd = "GET_GPI_PORT"
    vfctrl_cmd = "vfctrl_usb"

    # low nibble is ip_0 thru 3.
    # hi bit is mute mic, then down, up and action
    # natural behavior is 1 if not pressed, 0 when pressed
    action = 1
    volup = 2
    voldown = 4
    mute = 8

    def __init__(self):
        self.user_action_handler = None
        self.user_mute_handler = None
        self.user_volup_handler = None
        self.user_voldown_handler = None

        process = subprocess.Popen(
            ["sudo", self.vfctrl_cmd, "GET_GPI_READ_HEADER"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        out, err = process.communicate()
        # should probably verify 0 2 is returned!

        # auto start the switch read thread
        self._running = True
        self.thread_handle = threading.Thread(target=self.run, args=(1,))
        self.thread_handle.start()

        self.capabilities = {
            "user_volup_handler": "button",
            "user_voldown_handler": "button",
            "user_action_handler": "button",
            "user_mute_handler": "slider",
        }

    def get_capabilities(self):
        return self.capabilities

    def terminate(self):
        self._running = False

    def handle_action(self):
        if self.user_action_handler is not None:
            self.user_action_handler()

    def handle_voldown(self):
        if self.user_voldown_handler is not None:
            self.user_voldown_handler()

    def handle_volup(self):
        if self.user_volup_handler is not None:
            self.user_volup_handler()

    def handle_mute(self, val):
        if self.user_mute_handler is not None:
            self.user_mute_handler(val)

    def run(self, val):
        """usb must be polled"""
        while self._running:
            process = subprocess.Popen(
                [self.sudo_cmd, self.vfctrl_cmd, self.gpi_read_cmd],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

            out, err = process.communicate()
            out = out.decode("utf-8")
            err = err.decode("utf-8")

            if err is not None and err != "":
                # print("Creepy Internal Error #001! %s" % (err,))
                pass

            port_val = int(out.replace("GET_GPI_PORT: ", ""))

            if not (port_val & self.action):
                self.handle_action()

            if not (port_val & self.voldown):
                self.handle_voldown()

            if not (port_val & self.volup):
                self.handle_volup()

            self.handle_mute(port_val & self.mute)

            time.sleep(self.sleep_time)
