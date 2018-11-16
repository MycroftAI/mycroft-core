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

script=${0}
script=${script##*/}
cd -P "$( dirname "$SOURCE" )"
DIR="$( pwd )"
VIRTUALENV_ROOT=${VIRTUALENV_ROOT:-"${DIR}/.venv"}

function help() {
    echo "${script}:  Mycroft command/service launcher"
    echo "usage: ${script} [command] [params]"
    echo
    echo "Services:"
    echo "  all                      runs core services: bus, audio, skills, voice"
    echo "  debug                    runs core services, then starts the CLI"
    echo
    echo "Services:"
    echo "  audio                    the audio playback service"
    echo "  bus                      the messagebus service"
    echo "  skills                   the skill service"
    echo "  voice                    voice capture service"
    # echo "  wifi                     wifi setup service"
    echo "  enclosure                mark_1 enclosure service"
    echo
    echo "Tools:"
    echo "  cli                      the Command Line Interface"
    echo "  unittest                 run mycroft-core unit tests (requires pytest)"
    echo "  skillstest               run the skill autotests for all skills (requires pytest)"
    echo
    echo "Utils:"
    echo "  audiotest                attempt simple audio validation"
    echo "  audioaccuracytest        more complex audio validation"
    echo "  sdkdoc                   generate sdk documentation"
    echo
    echo "Examples:"
    echo "  ${script} all"
    echo "  ${script} cli"
    echo "  ${script} unittest"

    exit 1
}

_module=""
function name-to-script-path() {
    case ${1} in
        "bus")               _module="mycroft.messagebus.service" ;;
        "skills")            _module="mycroft.skills" ;;
        "audio")             _module="mycroft.audio" ;;
        "voice")             _module="mycroft.client.speech" ;;
        "cli")               _module="mycroft.client.text" ;;
        "audiotest")         _module="mycroft.util.audio_test" ;;
        "audioaccuracytest") _module="mycroft.audio-accuracy-test" ;;
        "enclosure")         _module="mycroft.client.enclosure" ;;

        *)
            echo "Error: Unknown name '${1}'"
            exit 1
    esac
}

function source-venv() {
    # Enter Python virtual environment, unless under Docker
    if [ ! -f "/.dockerenv" ] ; then
        source ${VIRTUALENV_ROOT}/bin/activate
    fi
}

first_time=true
function launch-process() {
    if ($first_time) ; then
        echo "Initializing..."
        "${DIR}/scripts/prepare-msm.sh"
        source-venv
        first_time=false
    fi

    name-to-script-path ${1}

    # Launch process in foreground
    echo "Starting $1"
    python3 -m ${_module} $_params
}

function launch-background() {
    if ($first_time) ; then
        echo "Initializing..."
        "${DIR}/scripts/prepare-msm.sh"
        source-venv
        first_time=false
    fi

    # Check if given module is running and start (or restart if running)
    name-to-script-path ${1}
    if pgrep -f "python3 -m ${_module}" > /dev/null ; then
        echo "Restarting: ${1}"
        "${DIR}/stop-mycroft.sh" ${1}
    else
        echo "Starting background service $1"
    fi

    # Security warning/reminder for the user
    if [[ "${1}" == "bus" ]] ; then
        echo "CAUTION: The Mycroft bus is an open websocket with no built-in security"
        echo "         measures.  You are responsible for protecting the local port"
        echo "         8181 with a firewall as appropriate."
    fi

    # Launch process in background, sending logs to standard location
    python3 -m ${_module} $_params >> /var/log/mycroft/${1}.log 2>&1 &
}

function launch-all() {
    echo "Starting all mycroft-core services"
    launch-background bus
    launch-background skills
    launch-background audio
    launch-background voice

    # Determine platform type
    if [[ -r /etc/mycroft/mycroft.conf ]] ; then
        mycroft_platform=$( jq -r ".enclosure.platform" < /etc/mycroft/mycroft.conf )
        if [[ $mycroft_platform = "mycroft_mark_1" ]] ; then
            # running on a Mark 1, start enclosure service
            launch-background enclosure
        fi
    fi
}

function check-dependencies() {
    if [ ! -f .installed ] || ! md5sum -c &> /dev/null < .installed ; then
        # Critical files have changed, dev_setup.sh should be run again
        if [ -f .dev_opts.json ] ; then
            auto_update=$( jq -r ".auto_update" < .dev_opts.json 2> /dev/null)
        else
            auto_update="false"
        fi

        if [ "$auto_update" == "true" ] ; then
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
shift
_params=$@

check-dependencies

case ${_opt} in
    "all")
        launch-all
        ;;

    "bus")
        launch-background ${_opt}
        ;;
    "audio")
        launch-background ${_opt}
        ;;
    "skills")
        launch-background ${_opt}
        ;;
    "voice")
        launch-background ${_opt}
        ;;

    "debug")
        launch-all
        launch-process cli
        ;;

    "cli")
        launch-process ${_opt}
        ;;

    # TODO: Restore support for Wifi Setup on a Picroft, etc.
    # "wifi")
    #    launch-background ${_opt}
    #    ;;
    "unittest")
        source-venv
        pytest test/unittests/ --cov=mycroft "$@"
        ;;
    "skillstest")
        source-venv
        pytest test/integrationtests/skills/discover_tests.py "$@"
        ;;
    "audiotest")
        launch-process ${_opt}
        ;;
    "audioaccuracytest")
        launch-process ${_opt}
        ;;
    "sdkdoc")
        source-venv
        cd doc
        make ${opt}
        cd ..
        ;;
    "enclosure")
        launch-background ${_opt}
        ;;

    *)
        help
        ;;
esac
