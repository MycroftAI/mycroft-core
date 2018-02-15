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

SOURCE="${BASH_SOURCE[0]}"

script=${0}
script=${script##*/}
DIR="$( cd -P "$( dirname "$SOURCE" )" && pwd )"
scripts_dir="$DIR/scripts"
mkdir -p $scripts_dir/logs

if [ -z "$WORKON_HOME" ]; then
    VIRTUALENV_ROOT=${VIRTUALENV_ROOT:-"${HOME}/.virtualenvs/mycroft"}
else
    VIRTUALENV_ROOT="$WORKON_HOME/mycroft"
fi

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
  echo "  wifi                     wifi setup service"
  echo "  enclosure                mark_1 enclosure service"
  echo
  echo "Tools:"
  echo "  cli                      the Command Line Interface"
  echo "  unittest                 run mycroft-core unit tests (requires nose2)"
  echo
  echo "Utils:"
  echo "  skill_container <skill>  container for running a single skill"
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

_script=""
function name-to-script-path() {
    case ${1} in
    "bus")             _script=${DIR}/mycroft/messagebus/service/main.py ;;
    "skills")          _script=${DIR}/mycroft/skills/main.py ;;
    "audio")           _script=${DIR}/mycroft/audio/main.py ;;
    "voice")           _script=${DIR}/mycroft/client/speech/main.py ;;
    "cli")             _script=${DIR}/mycroft/client/text/main.py ;;
    "wifi")            _script=${DIR}/mycroft/client/wifisetup/main.py ;;
    "skill_container") _script=${DIR}/mycroft/skills/container.py ;;
    "audiotest")       _script=${DIR}/mycroft/util/audio_test.py ;;
    "audioaccuracytest") _script=${DIR}/mycroft/audio-accuracy-test/audio_accuracy_test.py ;;
    "sdkdoc")          _script=${DIR}/doc/generate_sdk_docs.py ;;
    "enclosure")       _script=${DIR}/mycroft/client/enclosure/main.py ;;

    *)
        echo "Error: Unknown name '${1}'"
        exit 1
    esac
}

first_time=true
function launch-process() {
    if ($first_time) ; then
        echo "Initializing..."
        ${DIR}/scripts/prepare-msm.sh
        source ${VIRTUALENV_ROOT}/bin/activate
        first_time=false
    fi

    name-to-script-path ${1}

    # Launch process in background, sending log to scripts/log/mycroft-*.log
    echo "Starting $1"
    python ${_script} $_params
}

function launch-background() {
    if ($first_time) ; then
        echo "Initializing..."
        ${DIR}/scripts/prepare-msm.sh
        source ${VIRTUALENV_ROOT}/bin/activate
        first_time=false
    fi

    name-to-script-path ${1}

    # Check if already running
    if [[ $( ps aux ) = *${_script}* ]] ; then
        echo "Restarting: ${1}"
        source stop-mycroft.sh ${1}
    else
        echo "Starting background service $1"
    fi

    # Launch process in background, sending log to scripts/log/mycroft-*.log
    python ${_script} $_params >> ${scripts_dir}/logs/mycroft-${1}.log 2>&1 &
}

_opt=$1
shift
_params=$@

case ${_opt} in
  "all")
    echo "Starting all mycroft-core services"
    launch-background bus
    launch-background skills
    launch-background audio
    launch-background voice
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
    echo "Starting all mycroft-core services"
    launch-background bus
    launch-background skills
    launch-background audio
    launch-background voice
    launch-process cli
    ;;

  "cli")
    launch-process ${_opt}
    ;;
  "wifi")
    launch-background ${_opt}
    ;;
  "skill_container")
    launch-process ${_opt}
    ;;
  "unittest")
    nose2 -t ./ -s test/unittests/ --with-coverage \
        --config=test/unittests/unittest.cfg
    ;;
  "audiotest")
    launch-process ${_opt}
    ;;
  "audioaccuracytest")
    launch-process ${_opt}
    ;;
  "sdkdoc")
    launch-process ${_opt}
    ;;
  "enclosure")
    launch-process ${_opt}
    ;;

  *)
    help
    ;;
esac

