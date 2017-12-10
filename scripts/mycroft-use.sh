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

# this script is for the Mark 1 and Picroft units

user=$(whoami)
#Build being changed to
change_to=${1}
#path to mycroft-core checkout
path=${2:-"/home/${user}/mycroft-core"}
#currently installed package
current_pkg=$(cat /etc/apt/sources.list.d/repo.mycroft.ai.list)
stable_pkg="deb http://repo.mycroft.ai/repos/apt/debian debian main"
unstable_pkg="deb http://repo.mycroft.ai/repos/apt/debian debian-unstable main"

mark_1_package_list="mycroft-mark-1 mycroft-core mycroft-wifi-setup"
picroft_package_list="mycroft-picroft mycroft-core mycroft-wifi-setup"

# Determine the platform
mycroft_platform="null"
if [[ -r /etc/mycroft/mycroft.conf ]] ; then
   mycroft_platform=$( jq -r '.enclosure.platform' /etc/mycroft/mycroft.conf )
else
   if [[ "$(hostname)" == "picroft" ]] ; then
      mycroft_platform="picroft"
   elif [[ "$(hostname)" =~ "mark_1" ]] ; then
      mycroft_platform="mycroft_mark_1"
   fi
fi


function service_ctl {
    service=${1}
    action=${2}
    sudo /etc/init.d/${service} ${action}
}

function stop_mycroft {
    service_ctl mycroft-audio stop
    service_ctl mycroft-skills stop
    service_ctl mycroft-speech-client stop
    service_ctl mycroft-enclosure-client stop
    service_ctl mycroft-wifi-setup-client stop
    service_ctl mycroft-messagebus stop
}

function restart_mycroft {
    stop_mycroft

    service_ctl mycroft-audio start
    service_ctl mycroft-skills start
    service_ctl mycroft-speech-client start
    service_ctl mycroft-enclosure-client start
    service_ctl mycroft-wifi-setup-client start
    service_ctl mycroft-messagebus start
}

#Changes init scripts back to the original versions
function restore_init_scripts {
    if [ -f /etc/init.d/mycroft-skills.original ]; then

        # stop running Mycroft services
        stop_mycroft

        # swap back to original service scripts
        sudo sh -c 'cat /etc/init.d/mycroft-audio.original > /etc/init.d/mycroft-audio'
        sudo sh -c 'cat /etc/init.d/mycroft-enclosure-client.original > /etc/init.d/mycroft-enclosure-client'
        sudo sh -c 'cat /etc/init.d/mycroft-messagebus.original > /etc/init.d/mycroft-messagebus'
        sudo sh -c 'cat /etc/init.d/mycroft-skills.original > /etc/init.d/mycroft-skills'
        sudo sh -c 'cat /etc/init.d/mycroft-speech-client.original > /etc/init.d/mycroft-speech-client'
        sudo sh -c 'cat /etc/init.d/mycroft-wifi-setup-client.original > /etc/init.d/mycroft-wifi-setup-client'
        sudo rm /etc/init.d/*.original
        sudo chown -Rvf mycroft:mycroft /var/log/mycroft*
        sudo chown -Rvf mycroft:mycroft /tmp/mycroft/*
        sudo chown -Rvf mycroft:mycroft /var/run/mycroft*

        # reload daemon scripts
        sudo systemctl daemon-reload

        # restart services
        restart_mycroft
    fi
}

function github_init_scripts {
    if [ ! -f /etc/init.d/mycroft-skills.original ]; then

        stop_mycroft

        # save original scripts
        sudo sh -c 'cat /etc/init.d/mycroft-audio > /etc/init.d/mycroft-audio.original'
        sudo sh -c 'cat /etc/init.d/mycroft-enclosure-client > /etc/init.d/mycroft-enclosure-client.original'
        sudo sh -c 'cat /etc/init.d/mycroft-messagebus > /etc/init.d/mycroft-messagebus.original'
        sudo sh -c 'cat /etc/init.d/mycroft-skills > /etc/init.d/mycroft-skills.original'
        sudo sh -c 'cat /etc/init.d/mycroft-speech-client > /etc/init.d/mycroft-speech-client.original'
        sudo sh -c 'cat /etc/init.d/mycroft-wifi-setup-client > /etc/init.d/mycroft-wifi-setup-client.original'

        # switch to point a github install and run as the current user
# TODO Verify all of these
        sudo sed -i 's_.*SCRIPT=.*_SCRIPT="'${path}'/start.sh audio"_g' /etc/init.d/mycroft-audio
        sudo sed -i 's_.*RUNAS=.*_RUNAS='${user}'_g' /etc/init.d/mycroft-audio
        sudo sed -i 's_stop() {_stop() {\nPID=$(ps ax | grep mycroft/audio/ | awk '"'NR==1{print \$1; exit}'"')\necho "${PID}" > "$PIDFILE"_g' /etc/init.d/mycroft-audio

        sudo sed -i 's_.*SCRIPT=.*_SCRIPT="'${path}'/start.sh enclosure-client"_g' /etc/init.d/mycroft-enclosure-client
        sudo sed -i 's_.*RUNAS=.*_RUNAS='${user}'_g' /etc/init.d/mycroft-enclosure-client
        sudo sed -i 's_stop() {_stop() {\nPID=$(ps ax | grep mycroft/enclosure-client/ | awk '"'NR==1{print \$1; exit}'"')\necho "${PID}" > "$PIDFILE"_g' /etc/init.d/mycroft-enclosure-client

        sudo sed -i 's_.*SCRIPT=.*_SCRIPT="'${path}'/start.sh service"_g' /etc/init.d/mycroft-messagebus
        sudo sed -i 's_.*RUNAS=.*_RUNAS='${user}'_g' /etc/init.d/mycroft-messagebus
        sudo sed -i 's_stop() {_stop() {\nPID=$(ps ax | grep mycroft/messagebus/ | awk '"'NR==1{print \$1; exit}'"')\necho "${PID}" > "$PIDFILE"_g' /etc/init.d/mycroft-messagebus

        sudo sed -i 's_.*SCRIPT=.*_SCRIPT="'${path}'/start.sh skills"_g' /etc/init.d/mycroft-skills
        sudo sed -i 's_.*RUNAS=.*_RUNAS='${user}'_g' /etc/init.d/mycroft-skills
        sudo sed -i 's_stop() {_stop() {\nPID=$(ps ax | grep mycroft/skills/ | awk '"'NR==1{print \$1; exit}'"')\necho "${PID}" > "$PIDFILE"_g' /etc/init.d/mycroft-skills

        sudo sed -i 's_.*SCRIPT=.*_SCRIPT="'${path}'/start.sh voice"_g' /etc/init.d/mycroft-speech-client
        sudo sed -i 's_.*RUNAS=.*_RUNAS='${user}'_g' /etc/init.d/mycroft-speech-client
        sudo sed -i 's_stop() {_stop() {\nPID=$(ps ax | grep mycroft/client/ | awk '"'NR==1{print \$1; exit}'"')\necho "${PID}" > "$PIDFILE"_g' /etc/init.d/mycroft-speech-client

#        sudo sed -i 's_.*SCRIPT=.*_SCRIPT="'${path}'/start.sh voice"_g' /etc/init.d/mycroft-wifi-setup-client
#        sudo sed -i 's_.*RUNAS=.*_RUNAS='${user}'_g' /etc/init.d/mycroft-wifi-setup-client
#        sudo sed -i 's_stop() {_stop() {\nPID=$(ps ax | grep mycroft/client/ | awk '"'NR==1{print \$1; exit}'"')\necho "${PID}" > "$PIDFILE"_g' /etc/init.d/mycroft-wifi-setup-client

        # soft link the current user to the mycroft user's identity file
        sudo ln -s /home/mycroft/.mycroft/identity/identity2.json /home/${user}/.mycroft/identity/identity2.json

        sudo chown -Rvf ${user}:${user} /var/log/mycroft*
        sudo chown -Rvf ${user}:${user} /var/run/mycroft*
        sudo chown -Rvf ${user}:${user} /tmp/mycroft/*

        # reload daemon scripts
        sudo systemctl daemon-reload

        restart_mycroft

        echo "Running code in: "
    fi
}

function invoke_apt {
    if [ ${mycroft_platform} == "mycroft_mark_1" ] ; then
        echo "${1}ing the mycroft-mark-1 metapackage..."
        sudo apt-get ${1} mycroft-mark-1 -y
    elif [ ${mycroft_platform} == "picroft" ] ; then
        echo "${1}ing the mycroft-picroft metapackage..."
        sudo apt-get ${1} mycroft-picroft -y
    else
        # for unknown, just update the generic package
        echo "${1}ing the generic mycroft-core package..."
        sudo apt-get ${1} mycroft-core -y
    fi
}

function remove_all {
    if [ ${mycroft_platform} == "mycroft_mark_1" ] ; then
        echo "Removing the mycroft mark-1 packages..."
        sudo apt-get remove ${mark_1_package_list} -y
    elif [ ${mycroft_platform} == "picroft" ] ; then
        echo "Removing the picroft packages..."
        sudo apt-get remove ${picroft_package_list} -y
    else
        # for unknown, just update the generic package
        echo "Removing the generic mycroft-core package..."
        sudo apt-get remove mycroft-core -y
    fi
}

function change_build {
    build=${1}
    sudo sh -c 'echo '"${build}"' > /etc/apt/sources.list.d/repo.mycroft.ai.list'
    sudo apt-get update

    invoke_apt install
}

function stable_to_unstable_server {
    identity_path=/home/mycroft/.mycroft/identity/
    conf_path=/home/mycroft/.mycroft/

    # check if on stable (home-test.mycroft.ai) already
    cmp --silent ${conf_path}/mycroft.conf ${conf_path}/mycroft.conf.unstable
    if [ $? -eq 0 ] ; then
       echo "Already set to use the home-test.mycroft.ai server"
       return
    fi

    # point to test server
    echo "Changing mycroft.conf to point to test server api-test.mycroft.ai"
    if [ -f ${conf_path}mycroft.conf ]; then
        cp ${conf_path}mycroft.conf ${conf_path}mycroft.conf.stable
    else
        echo "could not find mycroft.conf, was it deleted?"
    fi
    if [ -f ${conf_path}mycroft.conf.unstable ]; then
        cp ${conf_path}mycroft.conf.unstable ${conf_path}mycroft.conf
    else
        rm -r ${conf_path}mycroft.conf
        echo '{"server": {"url":"https://api-test.mycroft.ai", "version":"v1", "update":true, "metrics":false }}' $(cat ${conf_path}mycroft.conf.stable) | jq -s add > ${conf_path}mycroft.conf
    fi

    # saving identity2.json to stable state
    echo "Pointing identity2.json to unstable and saving to identity2.json.stable"
    if [ -f ${identity_path}identity2.json ]; then
        mv ${identity_path}identity2.json ${identity_path}identity2.json.stable
    fi
    if [ -f /home/mycroft/.mycroft/identity/identity2.json.unstable ]; then
        cp ${identity_path}identity2.json.unstable ${identity_path}identity2.json
    else
        echo "NOTE:  This seems to be your first time switching to unstable. You will need to go to home-test.mycroft.ai to pair on unstable."
    fi

    restart_mycroft
    echo "Set to use the home-test.mycroft.ai server!"
}

function unstable_to_stable_server {
    # switching from unstable -> stable
    identity_path=/home/mycroft/.mycroft/identity/
    conf_path=/home/mycroft/.mycroft/

    # check if on stable (home.mycroft.ai) already
    cmp --silent ${conf_path}/mycroft.conf ${conf_path}/mycroft.conf.stable
    if [ $? -eq 0 ] ; then
       echo "Already set to use the home.mycroft.ai server"
       return
    fi

    # point api to production server
    echo "Changing mycroft.conf to point to production server api.mycroft.ai"
    if [ -f ${conf_path}mycroft.conf ]; then
       echo '{"server": {"url":"https://api-test.mycroft.ai", "version":"v1", "update":true, "metrics":false }}' $(cat ${conf_path}mycroft.conf) | jq -s add > ${conf_path}mycroft.conf.unstable
    else
       echo "could not find mycroft.conf, was it deleted?"
    fi
    if [ -f ${conf_path}mycroft.conf.stable ]; then
       cp ${conf_path}mycroft.conf.stable ${conf_path}mycroft.conf
    else
       echo "ERROR:  Could not find mycroft.conf.stable, was it deleted?, an easy fix would be to copy mycroft.conf.unstable to mycroft.conf but remove the server field"
    fi

    # saving identity2.json into unstable state, then copying identity2.json.stable to identity2.json
    echo "Pointing identity2.json to unstable and saving to identity2.json.unstable"
    if [ -f ${identity_path}identity2.json ]; then
        mv ${identity_path}identity2.json ${identity_path}identity2.json.unstable
    fi
    if [ -f ${identity_path}identity2.json.stable ]; then
        cp ${identity_path}identity2.json.stable ${identity_path}identity2.json
    else
        echo "Can not find identity2.json.stable, was it deleted? You may need to repair at home.mycroft.ai"
    fi

    restart_mycroft
    echo "Set to use the home.mycroft.ai server!"
}



if [ "${change_to}" = "unstable" ]; then
    # make sure user is running as sudo first
    if [ "$EUID" -ne 0 ] ; then
        echo "Please run with sudo"
        exit
    fi

    echo "Switching to unstable build..."
    if [ "${current_pkg}" = "${stable_pkg}" ]; then
        change_build "${unstable_pkg}"
    else
        echo "already on unstable"
    fi

    restore_init_scripts
elif [ "${change_to}" = "stable" ]; then
    # make sure user is running as sudo first
    if [ "$EUID" -ne 0 ] ; then
        echo "Please run with sudo"
        exit
    fi

        echo "Switching to stable build..."
        if [ "${current_pkg}" = "${unstable_pkg}" ]; then
            # Need to remove the package to make sure upgrade happens due to
            # difference in stable/unstable to package numbering schemes
            remove_all

            change_build "${stable_pkg}"
        else
            echo "already on stable"
        fi

        restore_init_scripts
elif [ "${change_to}" = "github" ]; then
    # make sure user is running as sudo first
    if [ "$EUID" -ne 0 ] ; then
        echo "Please run with sudo"
        exit
    fi

    echo "Switching to github..."
    if [ ! -d ${path} ]; then
        mkdir --parents "${path}"
        cd "${path}"
        cd ..
        git clone https://github.com/MycroftAI/mycroft-core.git "${path}"
    fi

    if [ -d ${path} ]; then
        if  [ -f /usr/local/bin/mimic ]; then
            echo "Mimic file exists"
            sed -i "s_.*'${TOP}/scripts/install-mimic.sh'.*_#'${TOP}/scripts/install-mimic.sh'_g" ${path}/dev_setup.sh
        else
            echo "file doesn't exist"
            sed -i "s_.*#'${TOP}/scripts/install-mimic.sh'.*_'${TOP}/scripts/install-mimic.sh'_g" ${path}/dev_setup.sh
        fi

        # Build the dev environment
        ${path}/dev_setup.sh

        # Switch init scripts to start the github version
        github_init_scripts
    else
        echo "repository does not exist"
    fi
elif [ "${change_to}" = "home" ]; then
    # make sure user is running as sudo first
    if [ "$EUID" -ne 0 ] ; then
        echo "Please run with sudo"
        exit
    fi
    unstable_to_stable_server
elif [ "${change_to}" = "home-test" ]; then
    # make sure user is running as sudo first
    if [ "$EUID" -ne 0 ] ; then
        echo "Please run with sudo"
        exit
    fi
    stable_to_unstable_server
else
    echo "usage: mycroft-use.sh [stable | unstable | home | home-test | github [<path>]]"
    echo "Switch between mycroft-core install methods"
    echo
    echo "Options:"
    echo "  stable           switch to the current debian package"
    echo "  unstable         switch to the unstable debian package"
    echo "  github [<path>]  switch to the mycroft-core/dev github repo"
    echo
    echo "  home-test        switch to the test backend (home-test.mycroft.ai)"
    echo "  home             switch to the main backend (home.mycroft.ai)"
    echo
    echo "Params:"
    echo "  <path>  default for github installs is /home/<user>/mycroft-core"
    echo
    echo "Examples:"
    echo "  mycroft-use.sh stable"
    echo "  mycroft-use.sh unstable"
    echo "  mycroft-use.sh home"
    echo "  mycroft-use.sh home-test"
    echo "  mycroft-use.sh github"
    echo "  mycroft-use.sh github /home/bill/projects/mycroft/custom"
fi
