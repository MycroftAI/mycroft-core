#!/usr/bin/env bash

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

function start-mycroft {
  mkdir -p logs
  screen -mdS mycroft-service -c mycroft-service.screen ./start.sh service
  screen -mdS mycroft-skills -c mycroft-skills.screen ./start.sh skills
  screen -mdS mycroft-voice -c mycroft-voice.screen ./start.sh voice
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
