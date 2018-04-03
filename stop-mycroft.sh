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
SCRIPTS="$DIR/scripts"
mkdir -p $SCRIPTS/logs

function help() {
  echo "${script}:  Mycroft service stopper"
  echo "usage: ${script} [service]"
  echo
  echo "Service:"
  echo "  all       ends core services: bus, audio, skills, voice"
  echo "  (none)    same as \"all\""
  echo "  bus       stop the Mycroft messagebus service"
  echo "  audio     stop the audio playback service"
  echo "  skills    stop the skill service"
  echo "  voice     stop voice capture service"
  echo
  echo "Examples:"
  echo "  ${script}"
  echo "  ${script} audio"

  exit 1
}

function process-running() {
    if [[ $( ps aux | grep "[p]ython .*${1}/main.py" ) ]] ; then
        return 0
    else
        return 1
    fi
}

function end-process() {

    if process-running $1 ; then
        pid=$( ps aux | grep "[p]ython .*${1}/main.py" | awk '{print $2}' )
        kill -SIGINT ${pid}

        c=1
        while [ $c -le 20 ]
        do
            if process-running $1 ; then
                sleep 0.1
                (( c++ ))
            else
                c=999   # end loop
            fi
        done

        if process-running $1 ; then
            echo "Killing $1..."
            kill -9 ${pid}
        fi
    fi
}



OPT=$1
shift

case ${OPT} in
  "all")
    ;&
  "")
    echo "Stopping all mycroft-core services"
    end-process service
    end-process skills
    end-process audio
    end-process speech
    ;;
  "bus")
    end-process service
    ;;
  "audio")
    end-process audio
    ;;
  "skills")
    end-process skills
    ;;
  "voice")
    end-process speech
    ;;


  *)
    help
    ;;
esac

