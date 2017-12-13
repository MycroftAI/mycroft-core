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
import sys
from mycroft.configuration.config import Configuration


def main():
    config = Configuration.get().get("enclosure", {})
    platform = config.get("platform", "linux").lower()
    if platform == "mark_1":
        from mycroft.client.enclosure import Mark1Enclosure
        enclosure = Mark1Enclosure()
    else:
        from mycroft.client.enclosure import Enclosure
        enclosure = Enclosure()
    try:
        enclosure.run()
    except Exception as e:
        print(e)
    finally:
        enclosure.shutdown()
        sys.exit()


if __name__ == "__main__":
    main()
