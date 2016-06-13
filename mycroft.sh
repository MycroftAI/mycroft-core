#!/bin/sh

screen -mdS mycroft-service ./start.sh service >> mycroft-service.log
screen -mdS mycroft-skills ./start.sh skills >> mycroft-skills.log
screen -mdS mycfoft-voice ./start.sh voice >> mycroft-voice.log
