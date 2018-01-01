#!/usr/bin/env bash

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

to_lower() {
    echo ${@,,}
}

user_input() {
    local var_name=$1
    local prompt=$2
    local regex=${3-^.+$}
    local error_msg=${4-Invalid input.}
    local format_input=${5-to_lower}
    
    while true; do
        read -p "$prompt " input
        input=$($format_input $input)  # To lowercase
        
        if [[ $input =~ $regex ]]; then
            break
        fi
        
        echo $error_msg
    done
    printf -v $var_name "$input"  # $var_name=$input
}

user_input_raw() {
    user_input "$1" "$2" "$3" "$4" 'echo'
}

input_lines() {
    local var_name=$1
    local prompt=$2
    
    read -p "$prompt " line
    lines=$line
    while [ -n "${line//[\n ]}" ]; do
        read -p "> " line
        lines="$(printf "$lines\n$line")"
    done
    printf -v $var_name "$lines"  # $var_name=$lines
}

skills_dir=/opt/mycroft/skills

if [ "$#" -gt "2" ] || [ "$1" = "-h" ]; then
    echo "Usage: $0"
    exit 0
fi

while true; do
    user_input skill_desc 'Enter short description (ie. "siren alarm" or "pizza orderer"):' "^[a-z ]+$" "Please use only letter and spaces."

    lang=${2-en-us}
    
    capital_desc=$(echo $skill_desc | sed -e "s/\b./\u\0/g")  # pizza orderer -> Pizza Orderer
    camel_case_desc=${capital_desc// }  # pizza orderer -> PizzaOrderer
    class_name=${camel_case_desc}Skill  # PizzaOrderer -> PizzaOrdererSkill
    folder_name=skill-${skill_desc// /-}  # pizza orderer -> skill-pizza-orderer
    handler_name=${skill_desc// /_}  # pizza orderer -> pizza_orderer
    dialog_name=${skill_desc// /.}  # pizza change -> pizza.orderer
    skill_dir=$skills_dir/$folder_name
    
    if [ -d "$skill_dir" ]; then
        echo "The corresponding skill folder, $skill_dir already exists."
        continue
    fi
    
    echo "Class name: $class_name"
    echo "Folder name: $folder_name"
    echo
    user_input status "Looks good? (y/n)" "^[yn]$"
    
    if [ "$status" = "y" ]; then
        break
    fi
done

user_input lang "Locale (default = en-us):" "^([a-z]+\-[a-z]+|)$" "Please leave empty or write locale in the format of xx-xx"
if [ -z "$lang" ]; then lang=en-us; fi

user_input_raw short_desc "Enter one line description (ie. Orders fresh pizzas from the store):"
input_lines long_desc "Enter a long description:"
input_lines examples "Enter example phrases (ie. Order a pizza.):"
user_input_raw author "Enter author:"
examples=$(echo "$examples" | sed -e 's/^/ * "/' | sed -e 's/$/"/')

mkdir -p "$skill_dir"

echo """## $capital_desc
$short_desc

## Description
$long_desc

## Examples
$examples

## Credits
$author
""" > "$skill_dir/README.md"

echo "Generated README.md"

keyword=$camel_case_desc

echo """from adapt.intent import IntentBuilder
from mycroft import MycroftSkill, intent_handler


class $class_name(MycroftSkill):
    def __init__(self):
        MycroftSkill.__init__(self)

    @intent_handler(IntentBuilder().require('$keyword'))
    def handle_${handler_name}(self, message):
        self.speak_dialog('$dialog_name')


def create_skill():
    return $class_name()
""" > "$skill_dir/__init__.py"

echo -e "*.pyc\nsettings.json\n" > $skill_dir/.gitignore
for i in "dialog" "vocab"; do mkdir -p "$skill_dir/$i/$lang"; done
echo "$skill_desc" > "$skill_dir/vocab/$lang/$keyword.voc"
echo "$skill_desc" > "$skill_dir/dialog/$lang/$dialog_name.dialog"

year=$(date +"%Y")
echo """Copyright $year $author

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the \"Software\"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED \"AS IS\", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
""" > "$skill_dir/LICENSE"

echo "Generated MIT license file. If you would like to choose a different license, please replace LICENSE."
echo

function on_ctrl_c() {
    echo
    echo "Removing partially created skill..."
    rm -rf "$skill_dir"
    exit $?
}
trap on_ctrl_c SIGINT

user_input status 'Would you like to initialize a git repo? (y/n)' "^[yn]$"
if [ "$status" = "y" ]; then
    cd "$skill_dir"
    git init
    git add .
    git commit -am "Initial commit"
    user_input github_name "Please enter your GitHub username (leave empty to skip):" "^([0-9a-z\-]{2,}|)$" "Please only use letters, numbers, and hyphens."
    if [ -n "$github_name" ]; then
        github_url="https://github.com/$github_name/$folder_name.git"
        git remote add origin "$github_url"
        echo 'To add to GitHub, create the repo "'$folder_name'" and run "git push -u origin master"'
    fi
    cd $OLDPWD
fi

echo
echo "Finished!"
echo "Wrote to $skill_dir"

if command -v tree >/dev/null; then
    cd "$skills_dir"
    echo
    tree --dirsfirst "$folder_name"
    cd $OLDPWD
fi

