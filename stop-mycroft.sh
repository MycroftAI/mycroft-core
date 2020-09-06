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
fi

help() {
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
    echo "  enclosure stop enclosure (hardware/gui interface) service"
    echo
    echo "Examples:"
    echo "  ${script}"
    echo "  ${script} audio"

    exit 0
}

process_running() {
    if [ "$( pgrep -f "python3 (.*)-m mycroft.*${1}" )" ] ; then
        return 0
    else
        return 1
    fi
}

end_process() {
    if process_running "$1" ; then
        # Find the process by name, only returning the oldest if it has children
        pid=$( pgrep -o -f "python3 (.*)-m mycroft.*${1}" )
        printf "Stopping %s (%s)..." "$1" "${pid}"
        kill -SIGINT "${pid}"

        # Wait up to 5 seconds (50 * 0.1) for process to stop
        c=1
        while [ $c -le 50 ] ; do
            if process_running "$1" ; then
                sleep 0.1
		c=$((c + 1))
            else
                c=999   # end loop
            fi
        done

        if process_running "$1" ; then
            echo "failed to stop."
            pid=$( pgrep -o -f "python3 (.*)-m mycroft.*${1}" )            
            printf "  Killing %s (%s)..." "$1" "${pid}"
            kill -9 "${pid}"
            echo "killed."
            result=120
        else
            echo "stopped."
            if [ $result -eq 0 ] ; then
                result=100
            fi
        fi
    fi
}


result=0  # default, no change


OPT=$1
shift

case ${OPT} in
    ""|"all")
        echo "Stopping all mycroft-core services"
        end_process skills
        end_process audio
        end_process speech
        end_process enclosure
        end_process messagebus.service
        ;;
    "bus")
        end_process messagebus.service
        ;;
    "audio")
        end_process audio
        ;;
    "skills")
        end_process skills
        ;;
    "voice")
        end_process speech
        ;;
    "enclosure")
        end_process enclosure
        ;;

    *)
        help
        ;;
esac

# Exit codes:
#     0   if nothing changed (e.g. --help or no process was running)
#     100 at least one process was stopped
#     120 if any process had to be killed
exit $result
