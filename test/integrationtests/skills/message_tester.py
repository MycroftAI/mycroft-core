#!/usr/bin/env python

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
"""
    This message tester lets a user input a Message event and a json test
    case, and allows the evaluation of the Message event based on the
    test case

    It is supposed to be run in the Mycroft virtualenv, and python-tk
    must be installed (on Ubuntu: apt-get install python-tk)
"""

from tkinter import Label, Button, Tk, NORMAL, END, DISABLED
from tkinter.scrolledtext import ScrolledText
import skill_tester
import ast

EXAMPLE_EVENT = '''{
  'expect_response': False,
  'utterance': u'Recording audio for 600 seconds'
}'''

EXAMPLE_TEST_CASE = '''{
  "utterance": "record",
  "intent_type": "AudioRecordSkillIntent",
  "intent": {
    "AudioRecordSkillKeyword": "record"
  },
  "expected_response": ".*(recording|audio)"
}'''


class MessageTester:
    def __init__(self, root):
        root.title("Message tester")
        Label(root, text="Enter message event below", bg="light green").pack()
        self.event_field = ScrolledText(root, width=180, height=10)
        self.event_field.pack()

        Label(root, text="Enter test case below", bg="light green").pack()
        self.test_case_field = ScrolledText(root, width=180, height=20)
        self.test_case_field.pack()

        Label(root, text="Test result:", bg="light green").pack()

        self.result_field = ScrolledText(root, width=180, height=10)
        self.result_field.pack()
        self.result_field.config(state=DISABLED)
        self.button = Button(root, text="Evaluate", fg="red",
                             command=self._clicked)
        self.button.pack()

        self.event_field.delete('1.0', END)
        self.event_field.insert('insert', EXAMPLE_EVENT)
        self.test_case_field.delete('1.0', END)
        self.test_case_field.insert('insert', EXAMPLE_TEST_CASE)

    def _clicked(self):
        event = self.event_field.get('1.0', END)
        test_case = self.test_case_field.get('1.0', END)

        evaluation = skill_tester.EvaluationRule(ast.literal_eval(test_case))
        evaluation.evaluate(ast.literal_eval(event))
        self.result_field.config(state=NORMAL)
        self.result_field.delete('1.0', END)
        self.result_field.insert('insert', evaluation.rule)
        self.result_field.config(state=DISABLED)


r = Tk()
app = MessageTester(r)
r.mainloop()
