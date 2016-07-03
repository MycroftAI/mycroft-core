#!/usr/bin/env bash
# exit on any error
set -Ee

WORKING_DIR=$PWD
TMP_DIR=/tmp
ARCH=`uname -m`
#download correct
case $ARCH in 
"x86_64")
    URL="https://developer.spotify.com/download/libspotify/libspotify-12.1.51-Linux-x86_64-release.tar.gz"
    ;;
"i686")
    URL="https://developer.spotify.com/download/libspotify/libspotify-12.1.51-Linux-i686-release.tar.gz"
    ;;
"armv6l")
    URL="https://developer.spotify.com/download/libspotify/libspotify-12.1.51-Linux-armv6-release.tar.gz"
    ;;
*)
    URL=""
    echo "$ARCH is not supported"
    ;;
esac
if [ $URL != "" ] ; then
    EXTRACTED=`echo $URL | sed 's,^[^ ]*/,,' | sed 's,\.tar\.gz,,'`
    wget $URL -O $TMP_DIR/libspotify.tar.gz
    cd $TMP_DIR
    tar -xvzf libspotify.tar.gz
    cd $EXTRACTED
    make install
    cd $WORKING_DIR
fi
