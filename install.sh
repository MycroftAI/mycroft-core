#!/usr/bin/env bash

case `uname` in
  Linux )
     DISTRO=""
     which pacman && { DISTRO="arch"; }
     which apt-get && {
        if [ `which sudo` ]; then
            DISTRO="debian";
        else
            DISTRO="docker";
        fi
     }
     which dnf && { DISTRO="fedora"; }
     if [ ! -z $DISTRO ]; then
        ./scripts/distro/install_$DISTRO.sh
        ./dev_setup.sh
     else
        echo "Sorry, we don't have a installation script for your distribution yet, feel free to create it or install manually, if you need any help ask us on Mycroft Chat"
     fi
     ;;
  * )
        echo "Sorry, right now Mycroft is only supported on linux distributions"
     ;;
esac