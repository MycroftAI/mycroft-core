#!/usr/bin/env bash

SOURCE="${BASH_SOURCE[0]}"
while [ -h "$SOURCE" ]; do
  DIR="$( cd -P "$( dirname "$SOURCE" )" && pwd )"
  SOURCE="$(readlink "$SOURCE")"
  [[ $SOURCE != /* ]] && SOURCE="$DIR/$SOURCE"
done
DIR="$( cd -P "$( dirname "$SOURCE" )" && pwd )"

function usage {
  echo
  echo "Quickly start, stop or restart Mycroft's esential services in detached screens"
  echo
  echo "usage: $0 [-h] (start|stop|restart)"
  echo "      -h             this help message"
  echo "      start          starts mycroft-service, mycroft-skills and mycroft-voice"
  echo "      stop           stops mycroft-service, mycroft-skills and mycroft-voice"
  echo "      restart        restarts mycroft-service, mycroft-skills and mycroft-voice"
  echo
  echo "screen tips:"
  echo "            run 'screen -list' to see all running screens"
  echo "            run 'screen -r <screen-name>' (e.g. 'screen -r mycroft-service') to reatach a screen"
  echo "            press ctrl + a, ctrl + d to detace the screen again"
  echo "            See the screen man page for more details"
  echo
}

function verify-start() {
  # check if screen for service was started
    if screen -list | grep -q "$1";
    then
      :
    else 
  # else echo tail logs/mycroft-service.log
      echo "$1 failed to start. The log is below:"
      echo
      tail $DIR/logs/$1.log
    exit 1
    fi
}


function start-mycroft {
  mkdir -p $DIR/logs
  screen -mdS mycroft-service -c $DIR/mycroft-service.screen $DIR/start.sh service
  sleep 1
  verify-start mycroft-service
  screen -mdS mycroft-skills -c $DIR/mycroft-skills.screen $DIR/start.sh skills
  sleep 1
  verify-start mycroft-skills
  screen -mdS mycroft-voice -c $DIR/mycroft-voice.screen $DIR/start.sh voice
  sleep 1
  verify-start mycroft-voice
}
function stop-mycroft {
  screen -XS mycroft-service quit
  screen -XS mycroft-skills quit
  screen -XS mycroft-voice quit
}

set -e

if [[ -z "$1" || "$1" == "-h" ]]
then
  usage
  exit 1
elif [ "$1" == "start" ]
then
  start-mycroft
  echo "Mycroft Started"
  exit 0
elif [ "$1" == "stop" ]
then
  stop-mycroft
  echo "Mycroft Stopped"
  exit 0
elif [ "$1" == "restart" ]
then
  stop-mycroft
  echo "Stopping Mycroft"
  start-mycroft
  echo "Mycroft restarted"
  exit 0
else
  usage
  exit 1
fi
