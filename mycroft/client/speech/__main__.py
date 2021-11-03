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
#
from mycroft.client.speech.service import SpeechClient
from mycroft.configuration import setup_locale
from mycroft.lock import Lock as PIDLock  # Create/Support PID locking file
from mycroft.util import (
    reset_sigint_handler,
    wait_for_exit_signal
)


def main():
    reset_sigint_handler()
    PIDLock("voice")
    setup_locale()
    service = SpeechClient()
    service.setDaemon(True)
    service.start()
    wait_for_exit_signal()


if __name__ == "__main__":
    main()
