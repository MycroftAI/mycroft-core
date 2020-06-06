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

# Verify and present the user with information about their installation of mycroft.
# Should be run as the mycroft user.
#
# To do: functionalize and allow for parametereized calls of each.
# rs 2017-05-05

function helpfunc() {
    echo "Usage: ${0} [FUNCTION]"
    echo " Functions include
  -v version
  -P python
  -p permissions
  -i internet
  -s system info
  -u audio
  -r running
  -m mimic
  -a run all checks
"
}

if [[ $# -eq 0 ]] ; then
    helpfunc && exit 1
fi

MYCROFT_HOME=""
RUN_AS_ROOT=1
source $( locate virtualenvwrapper.sh )

# log stuff and things
LOG_FILE=/tmp/my-info.$$.out
touch ${LOG_FILE}
if [[ ! -w "${LOG_FILE}" ]] ; then
    echo "Unable to write log file, output will be to screen only!"
    LOG_FILE="/dev/null"
    sleep 3
else
    echo "Logging to ${LOG_FILE}"
fi

# it's big, it's heavy, it's wood!
function mlog() {
    local timestamp="[$( date +"%Y-%m-%d %H:%M:%S" )]"
    message="$*"
    echo "${timestamp} ${message}" |tee -a ${LOG_FILE}
}

# Sup big perm.
function checkperms() {
if ! [[ -e "${1}" && -w "${1}" && -O "${1}"  ]] ; then
    if ! [[ -e "${1}" ]] ; then
        # doesn't exist?
        return 1
    fi
    if [[ -w "${1}" ]] ; then
        # lacks ownership
        return 2
    else
        # lacks write permissions
        return 3
    fi
else
    if [[ -x "${1}" ]] ; then
        # executable and awesome.
        return 10
    else
        # merely awesome
        return 0
    fi
fi
echo "If you can read this, we may need glasses."
}

# Check before we wreck:
function checkfiles() {
    mlog "Permission checks..."
    cat << EOF > /tmp/my-list.$$
${MYCROFT_HOME}
${MYCROFT_HOME}/scripts/logs
/tmp/mycroft/
/opt/mycroft/skills
EOF

    if [[ ${RUN_AS_ROOT} -eq 1 ]] ; then
        while read CHECKFN ; do
            checkperms "${CHECKFN}"
            case $? in
                "0") mlog " - ${CHECKFN} has viable permissions." ;;
                "1") mlog " = Error: ${CHECKFN} doesn't exist?" ;;
                "2") mlog " = Error: ${CHECKFN} not owned by ${UID}." ;;
                "3") mlog " = Error: ${CHECKFN} not writeable by ${UID}." ;;
                "10") mlog " - ${CHECKFN} is executable and has viable permissions." ;;
                *) mlog " = Error: unable to verify permissions on ${CHECKFN}." ;;
            esac
        done < /tmp/my-list.$$
    else
        mlog " = Error: permission checks skipped while running as root."
    fi
    rm -f /tmp/my-list.$$
}

# random info of potential interest
function checksysinfo() {
    mlog "System info..."
    mlog " - CPU: $( awk -F: '/model name/ { print $2;exit }' /proc/cpuinfo )"
    mlog " - $( echo "RAM Utilization:" && free -h )"
    mlog " - $( echo "Mycroft partition disk usage:" && df -h "${MYCROFT_HOME}" )"
    mlog " - $( echo "OS Info:" &&  cat /etc/*elease* )"
    mlog " - $( echo "Kernel version:" && uname -a )"
}

# -v
function checkversion() {
    mlog "Mycroft version is $( grep -B3 'END_VERSION_BLOCK' ${MYCROFT_HOME}/mycroft/version/__init__.py | cut -d' ' -f3 | tr -s '\012' '\056' )"
}

# do you want to do repeat?
function checkmimic() {
    mlog "Checking Mimic..."
    if hash mimic ; then
        mlog " - Mimic$( mimic --version | grep mimic )"
        mlog " - $( mimic -lv )"
    else
        mlog " = Error: Mimic binary not found. Mimic may not be installed?"
    fi
}

# pythoning!
function checkPIP() {
    mlog "Python checks"
    mlog " - Verifying ${MYCROFT_HOME}/requirements/requirements.txt:"
    if workon mycroft ; then
        pip list > /tmp/mycroft-piplist.$$

        while read reqline ; do
            IFS='==' read  -r -a PIPREQ <<< "$reqline"
            PIPREQVER=$( grep -i ^"${PIPREQ[0]} " /tmp/mycroft-piplist.$$ | cut -d'(' -f2 | tr -d '\051' )
            if [[ "${PIPREQVER}" == "${PIPREQ[2]}" ]] ; then
                mlog " -- pip ${PIPREQ[0]} version ${PIPREQ[2]}"
            else
                mlog " ~~ Warn: can't find ${PIPREQ[0]} ${PIPREQ[2]} in pip. (found ${PIPREQVER})"
            fi
        done < "${MYCROFT_HOME}/requirements.txt"
        deactivate
        mlog " - PIP list can be found at /tmp/mycroft-piplist.$$ to verify any issues."
    else
        mlog " = Error: Unable to enter the mycroft virtualenv, skipping python checks."
    fi
}

# a series of tubes
function checktubes() {
    mlog "Internet connectivity..."
    case "$( curl -s --max-time 2 -I http://home.mycroft.ai/ | sed 's/^[^ ]*  *\([0-9]\).*/\1/; 1q' )" in
        [23]) mlog " - HTTP connectivity to https://home.mycroft.ai worked!";;
        5) mlog " = Error: The web proxy won't let us through to https://home.mycroft.ai";;
        *) mlog " = Error: The network is down or very slow getting to https://home.mycroft.ai";;
    esac
}

# I prefer biking myself.
function checkrunning() {
    while read SCREEN_SESS ; do
        SESS_NAME=$( echo "${SCREEN_SESS}" | cut -d'(' -f1 | cut -d'.' -f2 )
        SESS_ID=$( echo "${SCREEN_SESS}" | cut -d'.' -f1 )
        if [[ $( ps flax| grep "$SESS_ID" | awk ' { print $4 } ' | grep -c "$SESS_ID" ) -eq 1 ]]; then
            mlog " - ${SESS_NAME} appears to be currently running."
        fi
    done < <(screen -list | grep mycroft)
}

# He's dead, Jim.
function checkpulse() {
    mlog "Sound settings..."
    if hash pactl && [[ ${RUN_AS_ROOT} -eq 1 ]] ; then
        mlog " - $( echo "Pulse Audio Defaults:" && pactl info | grep "Default S[i,o]" )"
        mlog " - $( echo "Pulse Audio Sinks:" && pactl list sinks | grep -e ^Sink  -e 'Name:' -e 'device.description' -e 'product_name' -e udev.id -e 'State:' )"
        mlog " - $( echo "Pulse Audio Sources:" && pactl list sources | grep -e ^Sourc -e 'Name:' -e 'device.description' -e 'product_name' -e udev.id -e 'State:' )"
    else
        mlog " = Error: Can't run pactl, skipping audio checks."
    fi
}

# ok, fine, go ahead and run this crazy thing
mlog "Starting ${0}"

# Who am i? Check if running sudo/as root/etc.
if [[ ${EUID} -ne ${UID} ]] ; then
    if [[ ${EUID} -gt 0 ]] ; then
        mlog " - Running as ${EUID} from UID ${UID}"
    else
        mlog " - Running with root permissions from UID ${UID}"
        RUN_AS_ROOT=0
    fi

else
    mlog " - Running as UID ${UID}"
fi

# where are we?
RUNDIR=$( readlink -f "${0}" | tr -s '\057' '\012' | sed \$d | tr -s '\012' '\057' )

# Where is mycroft installed?
if [[ -f "${RUNDIR}/mycroft-service.screen" && -f "${RUNDIR}/../mycroft/__init__.py" ]] ; then
    MYCROFT_HOME=$(cd "${RUNDIR}" && cd .. && pwd )
else
    if [[ -f "/opt/mycroft/mycroft/__init__.py" ]] ; then
        MYCROFT_HOME="/opt/mycroft/"
    else
        mlog " = Error: Having some difficulty in guessing the home Mycroft directory?"
        exit 200
    fi
fi

mlog " - Mycroft appears to be running in ${MYCROFT_HOME}"


while [[ $# -gt 0 ]] ; do
    opt="$1";
    shift;
    case "$opt" in
        "-v" ) checkversion ;;
        "-P") checkPIP ;;
        "-p") checkfiles ;;
        "-i") checktubes ;;
        "-s") checksysinfo ;;
        "-u") checkpulse;;
        "-r") checkrunning;;
        "-m") checkmimic;;
        "-a") checkversion ; checkrunning; checkPIP; checkfiles; checktubes; checksysinfo; checkpulse; checkmimic ;;
        *) helpfunc; exit 1;;
   esac
done

exit 0
