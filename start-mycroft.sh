#!/bin/sh

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

# This script is never sourced but always directly executed, so this is safe to do
SOURCE="$0"

script=${0}
script=${script##*/}

# If we're running systemwide it means MyCroft has been installed from distribution packaging
# In this case, some things like sourcing the virtual environment shouldn't happen
# Check if we're running systemwide by testing if the script is called start-mycroft.sh
# (which would be an in-source installation) or start-mycroft (which would be distro packaging)
systemwide=false
if [ "${script#*.sh}" = "$script" ]; then
	systemwide=true
fi

if [ $systemwide = false ]; then
	cd -P "$( dirname "$SOURCE" )" || exit
	DIR="$( pwd )"
	VIRTUALENV_ROOT=${VIRTUALENV_ROOT:-"${DIR}/.venv"}
fi

help() {
    echo "${script}:  Mycroft command/service launcher"
    echo "usage: ${script} [COMMAND] [restart] [params]"
    echo
    echo "Services COMMANDs:"
    echo "  all                      runs core services: bus, audio, skills, voice"
    echo "  debug                    runs core services, then starts the CLI"
    echo "  audio                    the audio playback service"
    echo "  bus                      the messagebus service"
    echo "  skills                   the skill service"
    echo "  voice                    voice capture service"
    # echo "  wifi                     wifi setup service"
    echo "  enclosure                mark_1 enclosure service"
    echo
    echo "Tool COMMANDs:"
    echo "  cli                      the Command Line Interface"
    
    if [ $systemwide = false ]; then
        echo "  unittest                 run mycroft-core unit tests (requires pytest)"
        echo "  skillstest               run the skill autotests for all skills (requires pytest)"
        echo "  vktest                   run the Voight Kampff integration test suite"
        echo
        echo "Util COMMANDs:"
        echo "  audiotest                attempt simple audio validation"
        echo "  wakewordtest             test selected wakeword engine"
        echo "  sdkdoc                   generate sdk documentation"
    fi
    echo
    echo "Options:"
    echo "  restart                  (optional) Force the service to restart if running"
    echo
    echo "Examples:"
    echo "  ${script} all"
    echo "  ${script} all restart"
    echo "  ${script} cli"
    if [ $systemwide = false ]; then
        echo "  ${script} unittest"
    fi

    exit 1
}

_module=""
name_to_script_path() {
    case ${1} in
        "bus")               _module="mycroft.messagebus.service" ;;
        "skills")            _module="mycroft.skills" ;;
        "audio")             _module="mycroft.audio" ;;
        "voice")             _module="mycroft.client.speech" ;;
        "cli")               _module="mycroft.client.text" ;;
        "audiotest")         _module="mycroft.util.audio_test" ;;
        "wakewordtest")      _module="test.wake_word" ;;
        "enclosure")         _module="mycroft.client.enclosure" ;;

        *)
            echo "Error: Unknown name '${1}'"
            exit 1
    esac
}

source_venv() {
    # Enter Python virtual environment, unless under Docker or when a virtualenv is already active
    virtualenv=$(python3 -c 'import sys; sys.stdout.write("1") if (hasattr(sys, "real_prefix") or (hasattr(sys, "base_prefix") and sys.base_prefix != sys.prefix)) else sys.stdout.write("0")')

    if [ ! -f "/.dockerenv" ] && [ "$virtualenv" -eq 0 ] ; then
        # shellcheck source=/dev/null
        . "${VIRTUALENV_ROOT}"/bin/activate
    fi
}

first_time=true
init_once() {
    if ($first_time) ; then
        echo "Initializing..."
        "${DIR}/scripts/prepare-msm.sh"
        source_venv
        first_time=false
    fi
}

launch_process() {
    if [ $systemwide = false ]; then
        init_once
    fi

    name_to_script_path "${1}"

    # Launch process in foreground
    echo "Starting $1"
    python3 -m ${_module} "$_params"
}

require_process() {
    # Launch process if not found
    name_to_script_path "${1}"
    if ! pgrep -f "python3 (.*)-m ${_module}" > /dev/null ; then
        # Start required process
        launch_background "${1}"
    fi
}

launch_background() {
    if [ $systemwide = false ]; then
        init_once
    fi

    # Check if given module is running and start (or restart if running)
    name_to_script_path "${1}"
    if pgrep -f "python3 (.*)-m ${_module}" > /dev/null ; then
        if ($_force_restart) ; then
            echo "Restarting: ${1}"
	    if [ $systemwide = false ]; then
                "${DIR}/stop-mycroft.sh" "${1}"
            else
		stop-mycroft "${1}"
	    fi
        else
            # Already running, no need to restart
            return
        fi
    else
        echo "Starting background service $1"
    fi

    # Security warning/reminder for the user
    if [ "${1}" = "bus" ] ; then
        echo "CAUTION: The Mycroft bus is an open websocket with no built-in security"
        echo "         measures.  You are responsible for protecting the local port"
        echo "         8181 with a firewall as appropriate."
    fi

    # Launch process in background
    # Send logs to old standard location if it exists
    # Otherwise send to XDG Base Directories cache location
    logdir="/var/log/mycroft"
    if [ ! -d "$logdir" ]; then
	    if [ ! -z ${XDG_CACHE_HOME+x} ]; then
		    logdir="$XDG_CACHE_HOME/mycroft"
	    else
		    logdir="$HOME/.cache/mycroft"
	    fi
    fi

    if [ ! -d "$logdir" ]; then
        mkdir -p "$logdir"
    fi

    python3 -m ${_module} "$_params" >> "$logdir/${1}.log" 2>&1 &
}

launch_all() {
    echo "Starting all mycroft-core services"
    launch_background bus
    launch_background skills
    launch_background audio
    launch_background voice
    launch_background enclosure
}

check_dependencies() {
    if [ -f .dev_opts.json ] ; then
        auto_update=$( jq -r ".auto_update" < .dev_opts.json 2> /dev/null)
    else
        auto_update="false"
    fi
    if [ "$auto_update" = "true" ] ; then
        # Check github repo for updates (e.g. a new release)
        git pull
    fi

    if [ ! -f .installed ] || ! md5sum -c 2>&1 > /dev/null < .installed ; then
        # Critical files have changed, dev_setup.sh should be run again
        if [ "$auto_update" = "true" ] ; then
            echo "Updating dependencies..."
            bash dev_setup.sh
        else
            echo "Please update dependencies by running ./dev_setup.sh again."
            if command -v notify-send >/dev/null ; then
                # Generate a desktop notification (ArchLinux)
                notify-send "Mycroft Dependencies Outdated" "Run ./dev_setup.sh again"
            fi
            exit 1
        fi
    fi
}

_opt=$1
_force_restart=false
shift
if [ "${1}" = "restart" ] || [ "${_opt}" = "restart" ] ; then
    _force_restart=true
    if [ "${_opt}" = "restart" ] ; then
        # Support "start-mycroft.sh restart all" as well as "start-mycroft.sh all restart"
        _opt=$1
    fi
    shift
fi
_params=$*

if [ $systemwide = false ]; then
	check_dependencies
fi

case ${_opt} in
    "all")
        launch_all
        ;;

    "bus")
        launch_background "${_opt}"
        ;;
    "audio")
        launch_background "${_opt}"
        ;;
    "skills")
        launch_background "${_opt}"
        ;;
    "voice")
        launch_background "${_opt}"
        ;;

    "debug")
        launch_all
        launch_process cli
        ;;

    "cli")
        require_process bus
        require_process skills
        launch_process "${_opt}"
        ;;

    # TODO: Restore support for Wifi Setup on a Picroft, etc.
    # "wifi")
    #    launch_background ${_opt}
    #    ;;
    "unittest")
        if [ $systemwide = false ]; then
            source_venv
            pytest test/unittests/ --cov=mycroft "$@"
	else
	    echo "Running tests is only supported from a local git checkout"
	fi
        ;;
    "singleunittest")
        if [ $systemwide = false ]; then
            source_venv
            pytest "$@"
        else
            echo "Running tests is only supported from a local git checkout"
	fi
        ;;
    "skillstest")
	if [ $systemwide = false ]; then
            source_venv
            pytest test/integrationtests/skills/discover_tests.py "$@"
        else
	    echo "Running tests is only supported from a local git checkout"
	fi
        ;;
    "vktest")
	if [ $systemwide = false ]; then
            bash "$DIR/bin/mycroft-skill-testrunner" vktest "$@"
        else
	    echo "Running tests is only supported from a local git checkout"
	fi
        ;;
    "audiotest")
        launch_process "${_opt}"
        ;;
    "wakewordtest")
        launch_process "${_opt}"
        ;;
    "sdkdoc")
	if [ $systemwide = false ]; then
            source_venv
            cd doc || exit
            make "${_params}"
            cd ..
        else
	    echo "Generating documentation is only supported from a local git checkout"
	fi
        ;;
    "enclosure")
        launch_background "${_opt}"
        ;;

    *)
        help
        ;;
esac
