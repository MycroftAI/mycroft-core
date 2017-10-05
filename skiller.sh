#!/bin/bash

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

SKILLS_FOLDER="/opt/mycroft/skills"

echo "What is the name of your skill *no spaces (ex HelloWorld)"
read NAME

SKILL_FOLDER="${SKILLS_FOLDER}/${NAME}"

SKILL_DIRS=( "dialog" "regex" "test" "vocab" )
for i in "${SKILL_DIRS[@]}"
do
    mkdir -p "${SKILL_FOLDER}/${i}"
done


echo "from adapt.intent import IntentBuilder
from mycroft.skills.core import MycroftSkill


class ${NAME}Skill(MycroftSkill):
    def __init__(self):
        super(${NAME}Skill, self).__init__(\"${NAME}Skill\")

    def initialize(self):
        pass

    def stop(self):
        pass


def create_skill():
    return ${NAME}Skill()" > "${SKILL_FOLDER}/__init__.py"

echo "${NAME}" > "${SKILL_FOLDER}/README.md"