#!/bin/sh

if [ ! -z $1 ]
then
     screen -XS mycroft-service quit
     screen -XS mycroft-skills quit
     screen -XS mycroft-voice quit
     echo "Mycroft Stopped"

else
     mkdir -p logs
     screen -mdS mycroft-service ./start.sh service >> logs/mycroft-service.log
     screen -mdS mycroft-skills ./start.sh skills >> logs/mycroft-skills.log
     screen -mdS mycroft-voice ./start.sh voice >> logs/mycroft-voice.log
     echo "Mycroft Started\nTo stop Mycroft use 'mycroft.sh stop'"
fi

