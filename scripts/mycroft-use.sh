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


function service_ctl {
    service=${1}
    action=${2}
    sudo /etc/init.d/${service} ${action}
}

#Changes init scripts back to the original versions
function original_init {
    service_ctl mycroft-skills stop
    service_ctl mycroft-speech-client stop
    service_ctl mycroft-messagebus stop
    sudo sh -c 'cat /etc/init.d/mycroft-skills.original > /etc/init.d/mycroft-skills'
    sudo sh -c 'cat /etc/init.d/mycroft-messagebus.original > /etc/init.d/mycroft-messagebus'
    sudo sh -c 'cat /etc/init.d/mycroft-speech-client.original > /etc/init.d/mycroft-speech-client'
    sudo rm /etc/init.d/*.original
    sudo chown -Rvf mycroft:mycroft /var/log/mycroft*
    sudo chown -Rvf mycroft:mycroft /tmp/mycroft/*
    sudo chown -Rvf mycroft:mycroft /var/run/mycroft*
    sudo systemctl daemon-reload
    service_ctl mycroft-messagebus start
    service_ctl mycroft-skills start
    service_ctl mycroft-speech-client start
}

function change_build {
    build=${1}
    sudo sh -c 'echo '"${build}"' > /etc/apt/sources.list.d/repo.mycroft.ai.list'
    sudo apt-get update
    sudo apt-get install mycroft-core -y
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

    service mycroft-skills restart
    service mycroft-speech-client restart
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
    echo "Changing mycroft.conf to point to test server api.mycroft.ai"
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

    # saving identity2.json into unstbale state, then copying identity2.json.stable to identity2.json
    echo "Pointing identity2.json to unstable and saving to identity2.json.unstable"
    if [ -f ${identity_path}identity2.json ]; then
        mv ${identity_path}identity2.json ${identity_path}identity2.json.unstable
    fi
    if [ -f ${identity_path}identity2.json.stable ]; then
        cp ${identity_path}identity2.json.stable ${identity_path}identity2.json
    else
        echo "Can not find identity2.json.stable, was it deleted? You may need to repair at home.mycroft.ai"
    fi

    service mycroft-skills restart
    service mycroft-speech-client restart
    echo "Set to use the home.mycroft.ai server!"
}

# make sure user is running as sudo first
if [ "${change_to}" = "unstable" ]; then

    if [ "$EUID" -ne 0 ] ; then
        echo "Please run with sudo"
        exit
    fi

    echo "Switching to unstable build..."
    if [ "${current_pkg}" = "${stable_pkg}" ]; then
        change_build "${unstable_pkg}"
        stable_to_unstable_server
    else
        echo "already on unstable"
    fi
    if [ -f /etc/init.d/mycroft-messagebus.original ]; then
        original_init
    fi
elif [ "${change_to}" = "stable" ]; then

    if [ "$EUID" -ne 0 ] ; then
        echo "Please run with sudo"
        exit
    fi

        echo "Switching to stable build..."
        if [ "${current_pkg}" = "${unstable_pkg}" ]; then
                sudo apt-get remove mycroft-core -y
                change_build "${stable_pkg}"
        else
            echo "already on stable"
        fi
        if [ -f /etc/init.d/mycroft-skills.original ]; then
                original_init
        fi
elif [ "${change_to}" = "github" ]; then

    if [ "$EUID" -ne 0 ] ; then
        echo "Please run with sudo"
        exit
    fi

    echo "Switching to github..."
    if [ -d ${path} ]; then
        if  [ -f /usr/local/bin/mimic ]; then
            echo "file exists"
            sed -i "s_.*'${TOP}/scripts/install-mimic.sh'.*_#'${TOP}/scripts/install-mimic.sh'_g" ${path}/dev_setup.sh
        else
            echo "file doesn't exist"
            sed -i "s_.*#'${TOP}/scripts/install-mimic.sh'.*_'${TOP}/scripts/install-mimic.sh'_g" ${path}/dev_setup.sh
        fi

        ${path}/build_host_setup_debian.sh
        ${path}/dev_setup.sh

        service_ctl mycroft-skills stop
        service_ctl mycroft-speech-client stop
        service_ctl mycroft-messagebus stop

        if [ ! -f /etc/init.d/mycroft-skills.original ]; then
            sudo sh -c 'cat /etc/init.d/mycroft-skills > /etc/init.d/mycroft-skills.original'
            sudo sh -c 'cat /etc/init.d/mycroft-messagebus > /etc/init.d/mycroft-messagebus.original'
            sudo sh -c 'cat /etc/init.d/mycroft-speech-client > /etc/init.d/mycroft-speech-client.original'
        fi

        sudo sed -i 's_.*SCRIPT=.*_SCRIPT="'${path}'/start.sh skills"_g' /etc/init.d/mycroft-skills
        sudo sed -i 's_.*RUNAS=.*_RUNAS='${user}'_g' /etc/init.d/mycroft-skills
        sudo sed -i 's_stop() {_stop() {\nPID=$(ps ax | grep mycroft/skills/ | awk '"'NR==1{print \$1; exit}'"')\necho "${PID}" > "$PIDFILE"_g' /etc/init.d/mycroft-skills

        sudo sed -i 's_.*SCRIPT=.*_SCRIPT="'${path}'/start.sh service"_g' /etc/init.d/mycroft-messagebus
        sudo sed -i 's_.*RUNAS=.*_RUNAS='${user}'_g' /etc/init.d/mycroft-messagebus
        sudo sed -i 's_stop() {_stop() {\nPID=$(ps ax | grep mycroft/messagebus/ | awk '"'NR==1{print \$1; exit}'"')\necho "${PID}" > "$PIDFILE"_g' /etc/init.d/mycroft-messagebus

        sudo sed -i 's_.*SCRIPT=.*_SCRIPT="'${path}'/start.sh voice"_g' /etc/init.d/mycroft-speech-client
        sudo sed -i 's_.*RUNAS=.*_RUNAS='${user}'_g' /etc/init.d/mycroft-speech-client
        sudo sed -i 's_stop() {_stop() {\nPID=$(ps ax | grep mycroft/client/ | awk '"'NR==1{print \$1; exit}'"')\necho "${PID}" > "$PIDFILE"_g' /etc/init.d/mycroft-speech-client

        sudo ln -s /home/mycroft/.mycroft/identity/identity2.json /home/${user}/.mycroft/identity/identity2.json

        sudo chown -Rvf ${user}:${user} /var/log/mycroft*
        sudo chown -Rvf ${user}:${user} /var/run/mycroft*
        sudo chown -Rvf ${user}:${user} /tmp/mycroft/*

        sudo systemctl daemon-reload

        service_ctl mycroft-messagebus start
        service_ctl mycroft-speech-client start
        service_ctl mycroft-skills start
    else
        echo "repository does not exist"
    fi
#   sudo reboot
elif [ "${change_to}" = "home" ]; then
    if [ "$EUID" -ne 0 ] ; then
        echo "Please run with sudo"
        exit
    fi
    unstable_to_stable_server
elif [ "${change_to}" = "home-test" ]; then
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
