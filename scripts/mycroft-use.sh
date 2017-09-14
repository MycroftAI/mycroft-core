#!/bin/bash
# Copyright 2016 Mycroft AI, Inc.
#
# This file is part of Mycroft Core.
#
# Mycroft Core is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Mycroft Core is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Mycroft Core.  If not, see <http://www.gnu.org/licenses/>.

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

        # point to test server
        echo "changing /home/mycroft/.mycroft.conf to point to test server api-test.mycroft.ai and saving the stable state to mycroft.conf.stable"
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
        echo "pointing /home/mycroft/.mycroft/identity2.json to unstable and saving stable state to identity2.json.stable"
        if [ -f ${identity_path}identity2.json ]; then 
            mv ${identity_path}identity2.json ${identity_path}identity2.json.stable
        fi
        if [ -f /home/mycroft/.mycroft/identity/identity2.json.unstable ]; then
                cp ${identity_path}identity2.json.unstable ${identity_path}identity2.json
        else
                echo "This seems to be your first time switching to unstable. You will need to go to home-test.mycroft.ai to pair on unstable"
        fi

		service mycroft-skills restart
}

function unstable_to_stable_server {
	    # switching from unstable -> stable
        identity_path=/home/mycroft/.mycroft/identity/
        conf_path=/home/mycroft/.mycroft/

        # point api to production server
        echo "changing /home/mycroft/.mycroft.conf to point to prod server api.mycroft.ai and saving the unstable state to mycroft.conf.unstable"
        if [ -f ${conf_path}mycroft.conf ]; then
            echo '{"server": {"url":"https://api-test.mycroft.ai", "version":"v1", "update":true, "metrics":false }}' $(cat ${conf_path}mycroft.conf) | jq -s add > ${conf_path}mycroft.conf.unstable
        else
            echo "could not find mycroft.conf, was it deleted?"
        fi
        if [ -f ${conf_path}mycroft.conf.stable ]; then
            cp ${conf_path}mycroft.conf.stable ${conf_path}mycroft.conf
        else 
            echo "could not find mycroft.conf.stable, was it deleted?, an easy fix would be to copy mycroft.conf.unstable to mycroft.conf but remove the server field"
        fi
        
        # saving identity2.json into unstbale state, then copying identity2.json.stable to identity2.json
        echo "pointing /home/mycroft/.mycroft/identity2.json to stable and saving unstable state to identity2.json.unstable"
        if [ -f ${identity_path}identity2.json ]; then     
            mv ${identity_path}identity2.json ${identity_path}identity2.json.unstable
        fi
        if [ -f ${identity_path}identity2.json.stable ]; then
            cp ${identity_path}identity2.json.stable ${identity_path}identity2.json	
        else
            echo "Can not find identity2.json.stable, was it deleted? You may need to repair at home.mycroft.ai"
        fi
            
	    service mycroft-skills restart
}

# make sure user is running as sudo first
if [ "$EUID" -ne 0 ]
    then echo "Please run as sudo to allow mycroft.conf to point to stable production server"
    exit
fi
if [ "${change_to}" = "unstable" ]; then
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
        echo "Switching to stable build..."
        if [ "${current_pkg}" = "${unstable_pkg}" ]; then
                sudo apt-get remove mycroft-core -y
                change_build "${stable_pkg}"
                unstable_to_stable_server
        else 
            echo "already on stable"
        fi
        if [ -f /etc/init.d/mycroft-skills.original ]; then
                original_init
        fi
elif [ "${change_to}" = "github" ]; then
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
#	sudo reboot
else
        echo "usage: mycroft-use.sh [stable | unstable | github [<path>]]"
	echo "Switch between mycroft-core install methods"
	echo
	echo "Options:"
	echo "  stable           switch to the current debian package"
	echo "  unstable         switch to the unstable debian package"
	echo "  github [<path>]  switch to the mycroft-core/dev github repo"
	echo
	echo "Params:"
        echo "  <path>  default for github installs is /home/<user>/mycroft-core"
	echo
        echo "Examples:"
        echo "  mycroft-use.sh stable"
        echo "  mycroft-use.sh unstable"
        echo "  mycroft-use.sh github"
        echo "  mycroft-use.sh github /home/bill/projects/mycroft/custom"
fi
