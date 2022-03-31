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

from mycroft.util import LOG


class MockSMBus:
    """A mock SMBus for use in dummy hardware components."""

    def __init__(self):
        LOG.info("Mock SMBus initialized.")

    def close(self):
        LOG.info("Mock SMBus closed.")

    def write_byte_data(*arg, **kwargs):
        LOG.debug("Writing byte data via mocked SMBus")

    def write_i2c_block_data(*arg, **kwargs):
        LOG.debug("Writing i2c block data via mocked SMBus")
