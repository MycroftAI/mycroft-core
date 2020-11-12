#!/bin/bash

while true;
do
  code=`grep "Pairing code:" /var/log/mycroft/skills.log | tail -1 | awk '{print $NF}'`;
  if [ ! -z $code ]; then
    pvmeta update mycroft.pairing_code=$code;
    exit 0;
  fi;
  sleep 1;
done
