#!/bin/sh

if [ ! -z $1 ]
then
     screen -XS mycroft-service quit
     screen -XS mycroft-skills quit
     screen -XS mycroft-voice quit
     echo "Mycroft Stopped"

else
     mkdir -p logs
     screen -mdS mycroft-service -c mycroft-service.screen ./start.sh service
     screen -mdS mycroft-skills -c mycroft-skills.screen ./start.sh skills
     screen -mdS mycroft-voice -c mycroft-voice.screen ./start.sh voice
     echo "Mycroft Started\nTo stop Mycroft use 'mycroft.sh stop'"
fi

