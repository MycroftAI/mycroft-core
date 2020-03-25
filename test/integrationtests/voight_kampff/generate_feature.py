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
#
from glob import glob
import json
from pathlib import Path
import sys

"""Convert existing intent tests to behave tests."""

TEMPLATE = """
  Scenario: {scenario}
    Given an english speaking user
     When the user says "{utterance}"
     Then "{skill}" should reply with dialog from "{dialog_file}.dialog"
"""


def json_files(path):
    """Generator function returning paths of all json files in a folder."""
    for json_file in sorted(glob(str(Path(path, '*.json')))):
        yield Path(json_file)


def generate_feature(skill, skill_path):
    """Generate a feature file provided a skill name and a path to the skill.
    """
    test_path = Path(skill_path, 'test', 'intent')
    case = []
    if test_path.exists() and test_path.is_dir():
        for json_file in json_files(test_path):
            with open(str(json_file)) as test_file:
                test = json.load(test_file)
                if 'utterance' and 'expected_dialog' in test:
                    utt = test['utterance']
                    dialog = test['expected_dialog']
                    # Simple handling of multiple accepted dialogfiles
                    if isinstance(dialog, list):
                        dialog = dialog[0]

                    case.append((json_file.name, utt, dialog))

    output = ''
    if case:
        output += 'Feature: {}\n'.format(skill)
    for c in case:
        output += TEMPLATE.format(skill=skill, scenario=c[0],
                                  utterance=c[1], dialog_file=c[2])

    return output


if __name__ == '__main__':
    print(generate_feature(*sys.argv[1:]))
