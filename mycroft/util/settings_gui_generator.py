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
import json
import yaml


class SettingsGuiGenerator:
    """Skill Settings Generator For GUI. """

    def __init__(self):
        """ Create a SettingList Object """
        self.settings_list = []

    def populate(self, skill_id, settings_file, settings_dict, file_type):
        """
        Populates settings list for current skill.

        Arguments:
            skill_id: ID of target skill.
            settings_file: Settings meta file from skill folder.
            settings_dict: Dictionary of current settings.json file.
        """

        if file_type == "json":
            with open(settings_file, 'r') as f:
                settingsmeta_dict = json.load(f)

                __skillMetaData = settingsmeta_dict.get('skillMetadata')
                for section in __skillMetaData.get('sections'):
                    self.settings_list.append(section)

        if file_type == "yaml":
            with open(settings_file, 'r') as f:
                settingsmeta_dict = yaml.safe_load(f)

                __skillMetaData = settingsmeta_dict.get('skillMetadata')
                for section in __skillMetaData.get('sections'):
                    self.settings_list.append(section)

        if settings_dict is not None:
            __updated_list = []
            for sections in self.settings_list:
                for fields in sections['fields']:
                    if "name" in fields:
                        if fields["name"] in settings_dict.keys():
                            fields["value"] = settings_dict[fields["name"]]

                __updated_list.append(sections)

            self.clear()
            self.settings_list = __updated_list

    def fetch(self):
        """Return Settings List """
        return self.settings_list

    def clear(self):
        """Clear Settings List """
        self.settings_list.clear()

    def update(self, settings_dict):
        """Getting Changed Settings & Update List.

        Arguments:
        settings_dict: Dictionary of current settings.json file.
        """
        __updated_list = []
        for sections in self.settings_list:
            for fields in sections['fields']:
                if "name" in fields:
                    if fields["name"] in settings_dict.keys():
                        fields["value"] = settings_dict[fields["name"]]

            __updated_list.append(sections)

        self.clear()
        self.settings_list = __updated_list
