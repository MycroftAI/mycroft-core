# Copyright 2022 Mycroft AI Inc.
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

import time
from math import exp, log

from mycroft.enclosure.hardware.MockSMBus import MockSMBus
from mycroft.enclosure.hardware.MycroftVolume.MycroftVolume import MycroftVolume
from mycroft.util.log import LOG

MAX_VOL = 84


class Volume(MycroftVolume):
    """A dummy Volume control class used for testing.

    This class has been kept as close as possible to the SJ201 version for
    testing purposes.
    """

    dev_addr = 0x2F
    vol_set_reg = 0x4C
    bus = ""

    def __init__(self):
        self.level = 0.5
        self.capabilities = {"range": (0.0, 1.0), "type": "MycroftTIAmp"}

        # auto start
        # self.bus = SMBus(1)
        # MOCKED FOR DUMMY CONTROLLER
        self.bus = MockSMBus()
        self.ti_start_sequence()

    def write_ti_data(self, addr, val):
        LOG.debug(
            "Write TI Data [DevAddr=%s] %s = %s"
            % (hex(self.dev_addr), hex(addr), hex(val))
        )
        self.bus.write_byte_data(self.dev_addr, addr, int(val))
        time.sleep(0.1)

    def ti_start_sequence(self):
        """
        Start Sequence for the TAS5806
        """
        LOG.info("Start the TI Amp")
        self.write_ti_data(0x01, 0x11)  # reset chip
        self.write_ti_data(0x78, 0x80)  # clear fault - works
        self.write_ti_data(0x01, 0x00)  # remove reset
        self.write_ti_data(0x78, 0x00)  # remove clear fault
        self.write_ti_data(0x33, 0x03)
        self.set_volume(0.5)
        self.write_ti_data(0x30, 0x01)
        self.write_ti_data(0x03, 0x00)  # Deep Sleep
        self.write_ti_data(0x03, 0x02)  # HiZ
        # Indicate the first coefficient of a BQ is starting to write
        self.write_ti_data(0x5C, 0x01)
        self.write_ti_data(0x03, 0x03)  # Play

    def get_capabilities(self):
        return self.capabilities

    def terminate(self):
        self.bus.close()

    def calc_log_y(self, x):
        """given x produce y. takes in an int
        0-100 returns a log oriented hardware
        value with larger steps for low volumes
        and smaller steps for loud volumes"""
        if x < 0:
            x = 0

        if x > 100:
            x = 100

        x0 = 0  # input range low
        x1 = 100  # input range hi

        y0 = MAX_VOL  # max hw vol
        y1 = 210  # min hw val

        p1 = (x - x0) / (x1 - x0)
        p2 = log(y0) - log(y1)
        pval = p1 * p2 + log(y1)

        return round(exp(pval))

    def calc_log_x(self, y):
        """given y produce x. takes in an int
        30-210 returns a value from 0-100"""
        if y < 0:
            y = MAX_VOL

        if y > 210:
            y = 210

        x0 = 0  # input range low
        x1 = 100  # input range hi

        y0 = MAX_VOL  # max hw vol
        y1 = 210  # min hw val

        x = x1 - x0
        p1 = (log(y) - log(y0)) / (log(y1) - log(y0))

        return x * p1 + x0

    def _set_hw_volume(self, vol):
        # takes an int between 90-210
        self.level = vol
        LOG.debug("DummyVolume: Setting ti amp to %s" % (self.level,))
        self.write_ti_data(self.vol_set_reg, int(vol))

    def _get_hw_volume(self):
        # returns an int between 90 - 210
        LOG.debug("DummyVolume: Getting ti amp value %s" % (self.level,))
        return self.level

    def set_volume(self, vol):
        # takes a float from 0.0 - 1.0
        LOG.debug("DummyVolume: Setting logical volume %s" % (vol,))
        hw_vol = self.calc_log_y(vol * 100.0)
        self._set_hw_volume(hw_vol)

    def get_volume(self):
        # returns a float from 0.0 - 1.0
        LOG.debug("DummyVolume: Getting logical volume from ti val %s" % (self.level,))
        return round(1.0 - float(self.calc_log_x(self._get_hw_volume())) / 100.0, 2)
