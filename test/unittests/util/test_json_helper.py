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
import json
import unittest

from os.path import dirname, join

from mycroft.util.json_helper import load_commented_json


class TestFileLoad(unittest.TestCase):

    def test_load(self):
        root_dir = dirname(__file__)
        # Load normal JSON file
        plainfile = join(root_dir, 'plain.json')
        with open(plainfile, 'r') as f:
            data_from_plain = json.load(f)

        # Load commented JSON file
        commentedfile = join(root_dir, 'commented.json')
        data_from_commented = load_commented_json(commentedfile)

        # Should be the same...
        self.assertEqual(data_from_commented, data_from_plain)


if __name__ == "__main__":
    unittest.main()
