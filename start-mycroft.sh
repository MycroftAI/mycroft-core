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

script=${0}
script=${script##*/}

DIR="$(realpath -- "$PWD")"
VIRTUALENV_ROOT=${VIRTUALENV_ROOT:-"${DIR}/.venv"}

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
    echo "  unittest                 run mycroft-core unit tests (requires pytest)"
    echo "  skillstest               run the skill autotests for all skills (requires pytest)"
    echo "  vktest                   run the Voight Kampff integration test suite"
    echo
    echo "Util COMMANDs:"
    echo "  audiotest                attempt simple audio validation"
    echo "  wakewordtest             test selected wakeword engine"
    echo "  sdkdoc                   generate sdk documentation"
    echo
    echo "Options:"
    echo "  restart                  (optional) Force the service to restart if running"
    echo
    echo "Examples:"
    echo "  ${script} all"
    echo "  ${script} all restart"
    echo "  ${script} cli"
    echo "  ${script} unittest"

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
    # Enter Python virtual environment, unless under Docker
    if [ ! -f "/.dockerenv" ] ; then
        . "${VIRTUALENV_ROOT}/bin/activate"
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
    init_once

    name_to_script_path "${1}"

    # Launch process in foreground
    echo "Starting $1"
    python3 -m ${_module} "$@"
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
    init_once

    # Check if given module is running and start (or restart if running)
    name_to_script_path "${1}"
    if pgrep -f "python3 (.*)-m ${_module}" > /dev/null ; then
        if ($_force_restart) ; then
            echo "Restarting: ${1}"
            "${DIR}/stop-mycroft.sh" "${1}"
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

    # Launch process in background, sending logs to standard location
    python3 -m ${_module} "$@" >> "/var/log/mycroft/${1}.log" 2>&1 &
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

    if [ ! -f .installed ] || ! md5sum -c > /dev/null 2>&1 < .installed ; then
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

if [ $# -eq 0 ]; then
	help
	return
fi

shift
if [ "${1}" = "restart" ] || [ "${_opt}" = "restart" ] ; then
    _force_restart=true
    if [ "${_opt}" = "restart" ] ; then
        # Support "start-mycroft.sh restart all" as well as "start-mycroft.sh all restart"
        _opt=$1
    fi

    if [ $# -gt 0 ]; then
	    shift
    fi
fi

if [ ! "${_opt}" = "cli" ] ; then
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
        source_venv
        pytest test/unittests/ --cov=mycroft "$@"
        ;;
    "singleunittest")
        source_venv
        pytest "$@"
        ;;
    "skillstest")
        source_venv
        pytest test/integrationtests/skills/discover_tests.py "$@"
        ;;
    "vktest")
        "$DIR/bin/mycroft-skill-testrunner" vktest "$@"
        ;;
    "audiotest")
        launch_process "${_opt}"
        ;;
    "wakewordtest")
        launch_process "${_opt}"
        ;;
    "sdkdoc")
        source_venv
        cd doc || exit 1  # Exit if doc directory doesn't exist
        make "$@"
        cd ..
        ;;
    "enclosure")
        launch_background "${_opt}"
        ;;

    *)
        help
        ;;
esac
