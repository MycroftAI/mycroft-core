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
from argparse import ArgumentParser

from msk.actions.upgrade import UpgradeAction
from msk.actions.upload import UploadAction
from msk.console_action import ConsoleAction
from msk.exceptions import NotUploaded


class SubmitAction(ConsoleAction):
    def __init__(self, args):
        try:
            self.action = UpgradeAction(args)
        except NotUploaded:
            self.action = UploadAction(args)

    @staticmethod
    def register(parser: ArgumentParser):
        parser.add_argument('skill_folder')

    def perform(self):
        self.action.perform()
