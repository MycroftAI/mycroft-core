import glob
import os
import json
import re
import string
from mycroft.messagebus.message import Message

PROJECT_ROOT = "/opt"


def discover_dialog():
    dialogs = {}
    skills = [
        skill for skill
        in glob.glob( os.path.join( PROJECT_ROOT, 'mycroft/skills/*' ) )
        if os.path.isdir( skill )
    ]

    for skill in skills:
        intent_files = [
            f for f
            in glob.glob( os.path.join( skill, 'test/intent/*.intent.json' ) )]
        print  intent_files



        for file in intent_files:
            output_file = open(file, 'r')
            output = output_file.read()
            data_json = json.loads(output)
            my_dict = {}
            my_dict = data_json


            # test if the JSON defines a single or multiple intent tests
            if my_dict['utterance'] is not None:
                # single case
                run_test(my_dict)
                pass
            else:
                # multiple test case?
                for item in my_dict:
                    if item['utterance'] is not None:
                        run_test(item)


def run_test(test_json):
    for test_item in test_json :
        if str(test_item) ==  "expected_output" :
            dialog_file = open(test_json['expected_output'], 'r')
            dialog_line = [line.rstrip('\n') for line in dialog_file]
            for i in range(len(dialog_line)):
                if '{{' in dialog_line[i]:
                    replaced_dialog = re.sub('\{\{(\S+)\}\}','.*', dialog_line[i])
                    compare_dialog_files(replaced_dialog)

def compare_dialog_files(regex_file):
    if '.*' in regex_file:
        m = re.match(regex_file,Message.data['utterance'])
        print m.group(1)
        # actual_output = Message.data['utterance'].split(' ')
        # re.match(Message.data['utterance'], regex_file)





discover_dialog()
