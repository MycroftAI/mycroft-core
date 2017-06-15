#!/usr/bin/env bash

./scripts/prepare-msm.sh

SOURCE="${BASH_SOURCE[0]}"
while [ -h "$SOURCE" ]; do
  DIR="$( cd -P "$( dirname "$SOURCE" )" && pwd )"
  SOURCE="$(readlink "$SOURCE")"
  [[ $SOURCE != /* ]] && SOURCE="$DIR/$SOURCE"
done
DIR="$( cd -P "$( dirname "$SOURCE" )" && pwd )"
SCRIPTS="$DIR/scripts"

function usage-exit {

cat << EOF

Quickly start, stop or restart Mycroft's essential services in detached screens

usage: $0 (start|stop|restart) [options]

      start          launch all necessary services to run mycroft
      stop           end all services
      restart        stop, then start all services
      -h, --help     this help message

start options:
      [nothing]      both cli and voice client
      -v, --voice    only voice client
      -c, --cli      only cli
      -d, --debug    only cli, in current terminal

restart options:
      (same as start)

screen tips:
            run 'screen -list' to see all running screens
            run 'screen -r <screen-name>' (e.g. 'screen -r mycroft-service') to reatach a screen
            press ctrl + a, ctrl + d to detach the screen again
            See the screen man page for more details

EOF

exit 1

}

mkdir -p $SCRIPTS/logs

function verify-start {
    if ! screen -list | grep -q "$1";
    then
      echo "$1 failed to start. The log is below:"
      echo
      tail $SCRIPTS/logs/$1.log
    exit 1
    fi
}

function screen-script {
  screen_name="$2"

  if [ "$1" == "log" ]; then
    args="$args -c $SCRIPTS/$screen_name.screen"
  elif [ "$1" != "no-log" ]; then
    echo "Invalid argument $1"
    exit 1
  fi

  shift
  shift

  screen -mdS $screen_name $args $@
  sleep 1
  verify-start $screen_name
  echo "Started $screen_name"
}

function start-mycroft {
  screen-script log "mycroft-$1" $DIR/start.sh $@
}

function start-mycroft-nolog {
  screen-script no-log "mycroft-$1" $DIR/start.sh $@
}

function start-mycroft-debug {
  $DIR/start.sh $@
}

function stop-screen {
  for i in $(screen -ls "$1"); do
    if echo $i | grep -q $1; then
      screen -XS $i quit && echo "Stopped $1" || echo "Could not stop $1"
    fi
  done
}

function stop-mycroft {
    stop-screen "mycroft-$1"
}

set -e

case "$1" in
"start")
  $0 stop
  start-mycroft service
  start-mycroft skills

  case "$2" in
  "")
    start-mycroft voice
    start-mycroft cli --quiet --simple
    ;;
  "-v"|"--voice")
    start-mycroft voice
    ;;
  "-c"|"--cli")
    start-mycroft cli --simple
    ;;
  "-d"|"--debug")
    start-mycroft-debug cli
    ;;
  *)
    echo "Usage"
    usage-exit
    ;;
  esac
  ;;

"stop")
  if [[ -n "$2" ]]; then usage-exit; fi
  stop-mycroft service
  stop-mycroft skills
  stop-mycroft voice
  stop-mycroft cli
  ;;

*)
  usage-exit
  ;;
esac
