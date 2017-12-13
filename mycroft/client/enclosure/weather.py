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


class EnclosureWeather(object):
    """
    Listens for Enclosure API commands to display indicators of the weather.

    Performs the associated command on Arduino by writing on the Serial port.
    """

    def __init__(self, writer):
        self.writer = writer

    def display(self, img_code=None, temp=None):
        if img_code:
            # Convert img_code to icon
            icon = None
            if img_code == 0:
                # sunny
                icon = "IICEIBMDNLMDIBCEAA"
            elif img_code == 1:
                # partly cloudy
                icon = "IIEEGBGDHLHDHBGEEA"
            elif img_code == 2:
                # cloudy
                icon = "IIIBMDMDODODODMDIB"
            elif img_code == 3:
                # light rain
                icon = "IIMAOJOFPBPJPFOBMA"
            elif img_code == 4:
                # raining
                icon = "IIMIOFOBPFPDPJOFMA"
            elif img_code == 5:
                # storming
                icon = "IIAAIIMEODLBJAAAAA"
            elif img_code == 6:
                # snowing
                icon = "IIJEKCMBPHMBKCJEAA"
            elif img_code == 7:
                # wind/mist
                icon = "IIABIBIBIJIJJGJAGA"

            if icon is not None and temp is not None:
                icon = "x=2," + icon
                msg = "weather.display=" + str(temp) + "," + str(icon)
                self.writer.write(msg)
