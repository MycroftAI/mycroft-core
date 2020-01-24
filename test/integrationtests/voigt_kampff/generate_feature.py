import json
from os.path import join
from pathlib import Path
import sys


TEMPLATE = """
  Scenario: {name}
    Given an english speaking user
     When the user says "{utterance}"
     Then "{name}" should reply with dialog from "{dialog_file}.dialog"
"""


def generate_feature(skill, skill_path):
    test_path = Path(join(skill_path, 'test', 'intent'))
    case = []
    if test_path.exists() and test_path.is_dir():
        for f in [f for f in test_path.iterdir() if f.suffix == '.json']:
            with open(str(f)) as test_file:
                test = json.load(test_file)
                if 'utterance' and 'expected_dialog' in test:
                    utt = test['utterance']
                    dialog = test['expected_dialog']
                    # Simple handling of multiple accepted dialogfiles
                    if isinstance(dialog, list):
                        dialog = dialog[0]

                    case.append((f.name, utt, dialog))

    output = ''
    if case:
        output += 'Feature: {}\n'.format(skill)
    for c in case:
        output += TEMPLATE.format(name=skill, utterance=c[1], dialog_file=c[2])

    return output


if __name__ == '__main__':
    print(generate_feature(*sys.argv[1:]))
