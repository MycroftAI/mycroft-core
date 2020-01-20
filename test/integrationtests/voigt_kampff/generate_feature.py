import json
from os.path import join
from pathlib import Path
import sys


TEMPLATE = """
  Scenario: {name}
    Given the skill path "{skill_path}"
     When the user says "{utterance}"
     Then the reply should be "{dialog_file}.dialog"
"""


def main(skill, skill_path):
    test_path = Path(join(skill_path, 'test', 'intent'))
    case = []
    if test_path.exists() and test_path.is_dir():
        for f in [f for f in test_path.iterdir() if f.suffix == '.json']:
            with open(str(f)) as test_file:
                test = json.load(test_file)
                if 'utterance' and 'expected_dialog' in test:
                    case.append((f.name,
                                 test['utterance'], test['expected_dialog']))

    if case:
        print('Feature: {}'.format(skill))
    for c in case:
        print(TEMPLATE.format(name=c[0], skill_path=skill_path,
                              utterance=c[1], dialog_file=c[2]))


if __name__ == '__main__':
    main(*sys.argv[1:])
