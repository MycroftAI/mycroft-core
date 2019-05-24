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

mycroft_root_dir="/opt/mycroft"  # Also change in configuration
skills_dir="${mycroft_root_dir}"/skills
# exit on any error
set -Ee

SOURCE="${BASH_SOURCE[0]}"
while [ -h "$SOURCE" ] ; do
    DIR="$( cd -P "$( dirname "$SOURCE" )" && pwd )"
    SOURCE="$(readlink "$SOURCE")"
    [[ $SOURCE != /* ]] && SOURCE="$DIR/$SOURCE"
done
DIR="$( cd -P "$( dirname "$SOURCE" )" && pwd )"

# Determine which user is running this script
setup_user=$USER
setup_group=$( id -gn $USER )

function found_exe() {
    hash "$1" 2>/dev/null
}

if found_exe sudo ; then
    # The main checks happen in dev_setup.sh, don't error here if we don't have sudo
    SUDO=sudo
fi

# change ownership of ${mycroft_root_dir} to ${setup_user } recursively
function change_ownership {
    echo "Changing ownership of" ${mycroft_root_dir} "to user:" ${setup_user} "with group:" ${setup_group}
    $SUDO chown -Rvf ${setup_user}:${setup_group} ${mycroft_root_dir}
}


if [[ ${IS_TRAVIS} != true ]] ; then
    if [ ! -d ${skills_dir} ] ; then
        echo "Create ${skills_dir}"
        $SUDO mkdir -p ${skills_dir}
        change_ownership
    fi

    if [ ! -w ${SKILLS_DIR} ] ; then
        change_ownership
    fi
fi

# fix ownership of ${mycroft_root_dir} if it is not owned by the ${setup_user}
if [[ $( stat -c "%U:%G" ${mycroft_root_dir} ) != "${setup_user}:${setup_group}" ]] ; then
    change_ownership
fi
