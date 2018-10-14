# -*- coding: utf-8 -*-
#
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
import unittest
import pathlib
import json

from mycroft.dialog import MustacheDialogRenderer


class DialogTest(unittest.TestCase):

    def setUp(self):
        self.stache = MustacheDialogRenderer()
        self.template_path = pathlib.Path('./mustache_templates')

    def test_fill_dialog(self):
        """ Test the loading and filling of valid simple mustache dialogs """
        for file in self.template_path.iterdir():
            if file.suffix == 'dialog':
                self.stache.load_template_file("template", file.absolute())
                context = json.load(file.with_suffix('.context.json').open('r', encoding='utf-8'))
                self.assertEqual(
                    self.stache.render("template", context),
                    file.with_suffix('result').open('r', encoding='utf-8').read()
                )


if __name__ == "__main__":
    unittest.main()
