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

from subprocess import call, check_output, CalledProcessError
from .MycroftVolume import MycroftVolume

# Definitions used when sending volume over i2c
VOL_MAX = 30
VOL_OFFSET = 15
VOL_SMAX = VOL_MAX - VOL_OFFSET
VOL_ZERO = 0


def clip(val, minimum, maximum):
    """Clips / limits a value to a specific range.
    Arguments:
        val: value to be limited
        minimum: minimum allowed value
        maximum: maximum allowed value
    """
    return min(max(val, minimum), maximum)


class Volume(MycroftVolume):
    def __init__(self):
        self.volume = 0.5
        self.capabilities = {"range": (0.0, 1.0), "type": "MycroftAmp"}

    def get_capabilities(self):
        return self.capabilities

    def set_hw_volume(self, pct):
        """Set the volume on hardware (which supports levels 0-63).

        Since the amplifier is quite powerful the range is limited to
        0 - 30.

        Arguments:
            pct (float): audio volume (0.0 - 1.0).
        """
        vol = int(VOL_SMAX * pct + VOL_OFFSET) if pct >= 0.01 else VOL_ZERO
        try:
            call(
                [
                    "/usr/sbin/i2cset",
                    "-y",  # force a write
                    "1",  # i2c bus number
                    "0x4b",  # stereo amp device address
                    str(vol),
                ]
            )  # volume level, 0-30
        except Exception as e:
            # self.log.error('Couldn\'t set volume. ({})'.format(e))
            pass

    def get_hw_volume(self):

        """Get the volume from hardware
        Returns: (float) 0.0 - 1.0 "percentage"
        """
        try:
            vol = check_output(["/usr/sbin/i2cget", "-y", "1", "0x4b"])
            # Convert the returned hex value from i2cget
            hw_vol = int(vol, 16)
            hw_vol = clip(hw_vol, 0, 63)
            self.volume = clip((hw_vol - VOL_OFFSET) / VOL_SMAX, 0.0, 1.0)
        except CalledProcessError as e:
            # self.log.info('I2C Communication error:  {}'.format(repr(e)))
            pass
        except FileNotFoundError:
            # self.log.info('i2cget couldn\'t be found')
            pass
        except Exception:
            # self.log.info('UNEXPECTED VOLUME RESULT:  {}'.format(vol))
            pass

        return self.volume

    def set_volume(self, vol):
        vol = float(vol / 10)
        self.set_hw_volume(vol)

    def get_volume(self):
        return self.level
