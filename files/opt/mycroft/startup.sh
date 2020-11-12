#!/bin/bash
adduser --disabled-password --gecos "" pulseaudio
addgroup pulseaudio pulse
addgroup root pulse

source /opt/mycroft/.venv/bin/activate
/usr/bin/pulseaudio --daemonize=no --log-level=1 --log-target=stderr --disallow-exit=true --exit-idle-time=180 -vvvv --system &

/opt/mycroft/pairing.sh &

export LC_ALL=C.UTF-8
/opt/mycroft/./start-mycroft.sh all
