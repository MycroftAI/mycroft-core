#!/bin/bash
#mycroft-use

user=$(whoami)
#Build being changed to
change_to=${1}
#path to mycroft-core checkout
path=${2:-"/home/"${user}"/mycroft-core"}
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

if [ "${change_to}" = "unstable" ]; then
        echo "Switching to unstable build..."
        if [ "${current_pkg}" = "${stable_pkg}" ]; then
                change_build "${unstable_pkg}"
        fi
        if [ -f /etc/init.d/mycroft-messagebus.original ]; then
                original_init
        fi
elif [ "${change_to}" = "stable" ]; then
        echo "Switching to stable build..."
        if [ "${current_pkg}" = "${unstable_pkg}" ]; then
                sudo apt-get remove mycroft-core -y
                change_build "${stable_pkg}"
        fi
        if [ -f /etc/init.d/mycroft-skills.original ]; then
                original_init
        fi
elif [ "${change_to}" = "github" ]; then
        echo "Switching to github..."
	if [ -d ${path} ]; then
	        if  [ -f /usr/local/bin/mimic ]; then
	                echo "file exists"
	                sed -i 's_.*"${TOP}/scripts/install-mimic.sh".*_#"${TOP}/scripts/install-mimic.sh"_g' ${path}/dev_setup.sh
	        else
	                echo "file doesn't exist"
	                sed -i 's_.*#"${TOP}/scripts/install-mimic.sh".*_"${TOP}/scripts/install-mimic.sh"_g' ${path}/dev_setup.sh
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
        echo "mycroft-use [stable | unstable | github]"
        echo "  Default path for github is /home/<user>/mycroft-core"
        echo "  Set custom path to mycroft-core checkout with second argument."
        echo "          ex. mycroft-use github /home/bill/projects/mycroft/<repository>" 
fi
