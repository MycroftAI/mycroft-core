#!/usr/bin/env bash
TOP=$(cd $(dirname $0) && pwd -L)

if [ -z "$WORKON_HOME" ]; then
    VIRTUALENV_ROOT=${VIRTUALENV_ROOT:-"${HOME}/.virtualenvs/mycroft"}
else
    VIRTUALENV_ROOT="$WORKON_HOME/mycroft"
fi

${TOP}/scripts/prepare-msm.sh

case $1 in
	"service") SCRIPT=${TOP}/mycroft/messagebus/service/main.py ;;
	"skills") SCRIPT=${TOP}/mycroft/skills/main.py ;;
	"audio") SCRIPT=${TOP}/mycroft/audio/main.py ;;
	"skill_container") SCRIPT=${TOP}/mycroft/skills/container.py ;;
	"voice") SCRIPT=${TOP}/mycroft/client/speech/main.py ;;
	"cli") SCRIPT=${TOP}/mycroft/client/text/main.py ;;
	"audiotest") SCRIPT=${TOP}/mycroft/util/audio_test.py ;;
	"collector") SCRIPT=${TOP}/mycroft_data_collection/cli.py ;;
	"unittest") SCRIPT=${TOP}/test/main.py ;;
	"audioaccuracytest") SCRIPT=${TOP}/mycroft/audio-accuracy-test/audio_accuracy_test.py ;;
	"sdkdoc") SCRIPT=${TOP}/doc/generate_sdk_docs.py ;;
    "enclosure") SCRIPT=${TOP}/mycroft/client/enclosure/main.py ;;
    "wifi") SCRIPT=${TOP}/mycroft/client/wifisetup/main.py ;;
	*) echo "Usage: start.sh [service | skills | skill_container | voice | cli | audiotest| audioaccuracytest | collector | unittest | enclosure | sdkdoc | wifi]"; exit ;;
esac

echo "Starting $@"

shift

source ${VIRTUALENV_ROOT}/bin/activate
PYTHONPATH=${TOP} python ${SCRIPT} $@
