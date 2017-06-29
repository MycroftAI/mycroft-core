#!/bin/bash

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