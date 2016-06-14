#!/bin/sh

mkdir -p logs
screen -mdS mycroft-service ./start.sh service >> logs/mycroft-service.log
screen -mdS mycroft-skills ./start.sh skills >> logs/mycroft-skills.log
screen -mdS mycroft-voice ./start.sh voice >> logs/mycroft-voice.log
