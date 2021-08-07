# Copyright (c) 2018 Mycroft AI, Inc.
#
# This file is part of Mycroft Skills Kit
# (see https://github.com/MycroftAI/mycroft-skills-kit).
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
from itertools import chain, count

import json
import re
from argparse import ArgumentParser
from glob import glob
from os import makedirs
from os.path import join, isdir, basename, isfile, splitext
from random import shuffle
from typing import Dict

from msk.console_action import ConsoleAction
from msk.exceptions import MskException
from msk.global_context import GlobalContext
from msk.lazy import Lazy
from msk.util import ask_yes_no, ask_input, read_file, read_lines, ask_choice, serialized


class TestCreator(GlobalContext):
    def __init__(self, folder):
        self.folder = folder

    init_file = Lazy(lambda s: join(s.folder, '__init__.py'))
    init_content = Lazy(lambda s: read_file(s.init_file) if isfile(s.init_file) else '')
    utterance = Lazy(lambda s: ask_input('Enter an example query:', lambda x: x))
    dialogs = Lazy(lambda s: [
        splitext(basename(i))[0]
        for i in glob(join(s.folder, 'dialog', s.lang, '*.dialog'))
    ])
    expected_dialog = Lazy(lambda s: ask_choice(
        'Choose expected dialog (leave empty to skip).', s.dialogs, allow_empty=True,
        on_empty='No dialogs available. Skipping...'
    ))

    padatious_creator = Lazy(lambda s: PadatiousTestCreator(s.folder))  # type: PadatiousTestCreator
    adapt_creator = Lazy(lambda s: AdaptTestCreator(s.folder))  # type: AdaptTestCreator
    intent_choices = Lazy(lambda s: list(chain(
        s.adapt_creator.intent_recipes,
        s.padatious_creator.intent_names
    )))

    @Lazy
    def intent_name(self):
        return ask_choice(
            'Which intent would you like to test?', self.intent_choices,
            on_empty='No existing intents found. Please create some first'
        )


class AdaptTestCreator(TestCreator):
    """
    Extracts Adapt intents from the source code

    Adapt's intents are made up of two components:
     - The "vocab definitions": words associated with a vocab name
     - The "intent recipe": list of vocab keywords that are required and optional for an intent
    """

    intent_regex = (
        r'''@(?:\\\n )*intent_handler  (?:\n )*\(  IntentBuilder  \(  ['"][^'"]*['"]  \)((?:  '''
        r'''\.  (?:optionally|require)  \(  ['"][a-zA-Z_]+['"]  \))*)\) \n'''
        r'''(?: \\\n)* def (?:\\\n )*([a-z_]+)'''
    ).replace('  ', r'[\s\n]*').replace(' ', r'\s*')

    parts_regex = r'''\.  (require|optionally)  \(  ['"]([a-zA-Z_]+)['"]  \)'''.replace('  ', r'[\s\n]*').replace(' ', '\s*')
    intent_recipe = Lazy(lambda s: s.intent_recipes[s.intent_name])

    @Lazy
    def utterance(self):
        while True:
            utterance = ask_input(
                'Enter an example query:',
                lambda x: x
            )

            missing_vocabs = [
                i for i in self.intent_recipe['require']
                if not any(j in utterance.lower() for j in self.vocab_defs.get(i, []))
            ]
            if missing_vocabs:
                print('Missing the following vocab:', ', '.join(missing_vocabs))
                if ask_yes_no('Continue anyways? (y/N)', False):
                    return utterance
            else:
                return utterance

    def extract_recipe(self, recipe_str):
        parts = {'require': [], 'optionally': []}
        for part_match in re.finditer(self.parts_regex, recipe_str):
            parts[part_match.group(1)].append(part_match.group(2))
        return parts

    @Lazy
    def intent_recipes(self) -> Dict[str, Dict[str, list]]:
        return {
            match.group(2): self.extract_recipe(match.group(1))
            for match in re.finditer(self.intent_regex, self.init_content)
        }

    @Lazy
    def vocab_defs(self):
        return {
            splitext(basename(content_file))[0]: list(chain(*(
                map(str.strip, i.lower().split('|'))
                for i in read_lines(content_file)
            )))
            for content_file in
            glob(join(self.folder, 'vocab', self.lang, '*.voc')) + glob(join(self.folder, 'locale', self.lang, '*.voc')) +
            glob(join(self.folder, 'regex', self.lang, '*.rx')) + glob(join(self.folder, 'locale', self.lang, '*.rx'))
        }

    @Lazy
    def utterance_data(self):
        utterance_left = self.utterance.lower()
        utterance_data = {}

        for key, start_message in [
            ('require', 'Required'),
            ('optionally', 'Optional')
        ]:
            if not self.intent_recipe[key]:
                continue

            print()
            print('===', start_message, 'Tags', '===')
            for vocab_name in sorted(self.intent_recipe[key]):
                vocab_value = ask_input(
                    vocab_name + ':', lambda x: not x or x.lower() in utterance_left,
                    'Response must be in the remaining utterance: ' + utterance_left
                )
                if vocab_value:
                    utterance_data[vocab_name] = vocab_value
                    utterance_left = utterance_left.replace(vocab_value.lower(), '')

        return utterance_data

    @Lazy
    @serialized
    def recipe_str(self):
        for key, name in [('require', 'Required'), ('optionally', 'Optional')]:
            if not self.intent_recipe[key]:
                continue

            yield ''
            yield '===', name, 'Vocab', '==='
            for vocab_name in sorted(self.intent_recipe[key]):
                words = self.vocab_defs.get(vocab_name, ['?'])
                yield '{}: {}'.format(vocab_name, ', '.join(
                    words[:6] + ['...'] * (len(words) > 6)
                ))

    @Lazy
    def test_case(self) -> dict:
        if self.intent_name not in self.intent_recipes:
            return {}

        print(self.recipe_str)
        print()

        test_case = {'utterance': self.utterance}
        if self.utterance_data:
            test_case['intent'] = self.utterance_data
        test_case['intent_type'] = self.intent_name
        if self.expected_dialog:
            test_case['expected_dialog'] = self.expected_dialog
        return test_case


class PadatiousTestCreator(TestCreator):
    intent_files = Lazy(lambda s: glob(join(s.folder, 'vocab', s.lang, '*.intent')) + glob(join(s.folder, 'locale', s.lang, '*.intent')))
    intent_names = Lazy(lambda s: {
        basename(intent_file): intent_file for intent_file in s.intent_files
    })
    intent_file = Lazy(lambda s: s.intent_names.get(s.intent_name, ''))
    entities = Lazy(lambda s: {
        splitext(basename(entity_file))[0]: read_lines(entity_file)
        for entity_file in glob(join(s.folder, 'vocab', s.lang, '*.entity')) + glob(join(s.folder, 'locale', s.lang, '*.entity'))
    })

    intent_lines = Lazy(lambda s: read_lines(s.intent_file))
    entity_names = Lazy(lambda s: set(re.findall(r'(?<={)[a-z_]+(?=})', '\n'.join(s.intent_lines))))

    @Lazy
    @serialized
    def entities_str(self) -> str:
        if not self.entities:
            return
        yield '=== Entity Examples ==='
        for entity_name, lines in sorted(self.entities.items()):
            sample = ', '.join(lines)
            yield '{}: {}'.format(
                entity_name, sample[:50] + '...' * (len(sample) > 50)
            )

    @Lazy
    @serialized
    def intent_str(self) -> str:
        shuffle(self.intent_lines)
        yield '=== Intent Examples ==='
        yield '\n'.join(self.intent_lines[:6] + ['...'] * (len(self.intent_lines) > 6))

    @Lazy
    def utterance_data(self) -> dict:
        utterance_data = {}
        utterance_left = self.utterance

        print()
        print('=== Entity Tags ===')
        for entity_name in sorted(self.entity_names):
            entity_value = ask_input(
                entity_name + ':', lambda x: not x or x in utterance_left,
                'Response must be in the remaining utterance: ' + utterance_left
            )
            if entity_value:
                utterance_data[entity_name] = entity_value
                utterance_left = utterance_left.replace(entity_value, '')
        return utterance_data

    @Lazy
    def test_case(self) -> {}:
        if self.intent_name not in self.intent_names:
            return {}

        print()
        print(self.intent_str)
        print()
        if self.entities_str:
            print(self.entities_str)
            print()

        test_case = {'utterance': self.utterance}
        if self.entity_names and self.utterance_data:
            test_case['intent'] = self.utterance_data
        test_case['intent_type'] = self.intent_name
        if self.expected_dialog:
            test_case['expected_dialog'] = self.expected_dialog
        return test_case


class CreateTestAction(ConsoleAction):
    def __init__(self, args):
        self.folder = args.skill_folder

    @staticmethod
    def register(parser: ArgumentParser):
        parser.add_argument('skill_folder')

    def find_intent_test_file(self, intent_name):
        def create_name(i):
            return join(self.folder, 'test', 'intent', '{}.{}.intent.json'.format(intent_name, i))

        for i in count():
            name = create_name(i)
            if not isfile(name):
                return name

    def perform(self):
        if not isdir(self.folder):
            raise MskException('Skill folder at {} does not exist'.format(self.folder))

        if not isfile(join(self.folder, '__init__.py')):
            if not ask_yes_no("Folder doesn't appear to be a skill. Continue? (y/N)", False):
                return

        makedirs(join(self.folder, 'test', 'intent'), exist_ok=True)

        creator = TestCreator(self.folder)
        test_case = creator.adapt_creator.test_case or creator.padatious_creator.test_case

        intent_test_file = self.find_intent_test_file(creator.intent_name)
        with open(intent_test_file, 'w') as f:
            json.dump(test_case, f, indent=4, sort_keys=True)
        print('Generated test file:', intent_test_file)
