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

SOURCE="${BASH_SOURCE[0]}"
while [ -h "$SOURCE" ]; do
  DIR="$( cd -P "$( dirname "$SOURCE" )" && pwd )"
  SOURCE="$(readlink "$SOURCE")"
  [[ $SOURCE != /* ]] && SOURCE="$DIR/$SOURCE"
done
DIR="$( cd -P "$( dirname "$SOURCE" )" && pwd )"
PARENTDIR=$(dirname "$DIR")
SYSTEM_CONFIG="$PARENTDIR/mycroft/configuration/mycroft.conf"

function get_config_value() {
  key="$1"
  default="$2"
  value="null"
  for file in ~/.mycroft/mycroft.conf /etc/mycroft/mycroft.conf $SYSTEM_CONFIG;   do
    if [[ -r $file ]] ; then
        # remove comments in config for jq to work
        # assume they may be preceded by whitespace, but nothing else
        parsed="$( sed 's:^\s*//.*$::g' $file )"
        echo "$parsed" >> "$PARENTDIR/mycroft/configuration/sys.conf"
        value=$( jq -r "$key" "$PARENTDIR/mycroft/configuration/sys.conf" )
        if [[ "${value}" != "null" ]] ;  then
            rm -rf $PARENTDIR/mycroft/configuration/sys.conf
            echo "$value"
            return
        fi
    fi
  done
  echo "$default"
}


mycroft_root_dir='/opt/mycroft'
skills_dir="$(get_config_value '.skills.directory' '/opt/mycroft/skills')"

# exit on any error
set -Ee

chmod +x ${DIR}/../msm/msm

# Determine which user is running this script
setup_user=$USER

# change ownership of ${mycroft_root_dir} to ${setup_user } recursively 
function change_ownership {
    echo "Changing ownership of" ${mycroft_root_dir} "to user:" ${setup_user} "with group:" ${setup_user}
            sudo chown -Rvf ${setup_user}:${setup_user} ${mycroft_root_dir}
}


if [[ ${IS_TRAVIS} != true ]]; then
    if [ ! -d ${skills_dir} ]; then
        echo "Create /opt/mycroft/skills"
        sudo mkdir -p ${skills_dir}
	change_ownership
    fi

    if [ ! -w ${SKILLS_DIR} ]; then
        change_ownership
    fi
fi

# fix ownership of ${mycroft_root_dir} if it is not owned by the ${setup_user}
if [[ `stat -c "%U:%G" /opt/mycroft` != "${setup_user}:${setup_user}" ]]; then
    change_ownership
fi
