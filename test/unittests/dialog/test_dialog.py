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

from mycroft.dialog import MustacheDialogRenderer, DialogLoader, get
from mycroft.util import resolve_resource_file


class DialogTest(unittest.TestCase):
    def setUp(self):
        self.stache = MustacheDialogRenderer()
        self.topdir = pathlib.Path(__file__).parent

    def test_general_dialog(self):
        """ Test the loading and filling of valid simple mustache dialogs """
        template_path = self.topdir.joinpath('./mustache_templates')
        for file in template_path.iterdir():
            if file.suffix == '.dialog':
                self.stache.load_template_file(file.name, str(file.absolute()))
                context = json.load(
                    file.with_suffix('.context.json').open(
                        'r', encoding='utf-8'))
                self.assertEqual(
                    self.stache.render(file.name, context),
                    file.with_suffix('.result').open('r',
                                                     encoding='utf-8').read())

    def test_unknown_dialog(self):
        """ Test for returned file name literals in case of unkown dialog """
        self.assertEqual(
            self.stache.render("unknown.template"), "unknown template")

    def test_multiple_dialog(self):
        """
        Test the loading and filling of valid mustache dialogs
        where a dialog file contains multiple text versions
        """
        template_path = self.topdir.joinpath('./mustache_templates_multiple')
        for file in template_path.iterdir():
            if file.suffix == '.dialog':
                self.stache.load_template_file(file.name, str(file.absolute()))
                context = json.load(
                    file.with_suffix('.context.json').open(
                        'r', encoding='utf-8'))
                results = [
                    line.strip() for line in file.with_suffix('.result').open(
                        'r', encoding='utf-8')
                ]
                # Try all lines
                for index, line in enumerate(results):
                    self.assertEqual(
                        self.stache.render(
                            file.name, index=index, context=context),
                        line.strip())
                # Test random index function
                # (bad test because non-deterministic?)
                self.assertIn(
                    self.stache.render(file.name, context=context), results)

    def test_comment_dialog(self):
        """
        Test the loading and filling of valid mustache dialogs
        where a dialog file contains multiple text versions
        """
        template_path = self.topdir.joinpath('./mustache_templates_comments')
        for f in template_path.iterdir():
            if f.suffix == '.dialog':
                self.stache.load_template_file(f.name, str(f.absolute()))
                results = [line.strip()
                           for line in f.with_suffix('.result').open('r')]
                # Try all lines
                for index, line in enumerate(results):
                    self.assertEqual(self.stache.render(f.name, index=index),
                                     line.strip())

    def test_dialog_loader(self):
        template_path = self.topdir.joinpath('./multiple_dialogs')
        loader = DialogLoader()
        renderer = loader.load(template_path)
        self.assertEqual(renderer.render('one'), 'ONE')
        self.assertEqual(renderer.render('two'), 'TWO')

    def test_dialog_loader_missing(self):
        template_path = self.topdir.joinpath('./missing_dialogs')
        loader = DialogLoader()
        renderer = loader.load(template_path)
        self.assertEqual(renderer.render('test'), 'test')

    def test_get(self):
        phrase = 'i didn\'t catch that'
        res_file = pathlib.Path('text/en-us/').joinpath(phrase + '.dialog')
        print(res_file)
        resource = resolve_resource_file(str(res_file))
        with open(resource) as f:
            results = [line.strip() for line in f]
        string = get(phrase)
        self.assertIn(string, results)

        # Check that the filename is returned if phrase is missing for lang
        string = get(phrase, lang='ne-ne')
        self.assertEqual(string, phrase)

        # Check that name is retured if phrase is missing
        string = get('testing aardwark')
        self.assertEqual(string, 'testing aardwark')


if __name__ == "__main__":
    unittest.main()
