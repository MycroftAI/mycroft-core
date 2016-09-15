#!/usr/bin/env bash

sudo pacman -S \
    git \
    python2 \
    python2-pip \
    python2-setuptools \
    python2-virtualenv \
    python2-gobject \
    python2-virtualenvwrapper \
    libtool \
    libffi \
    openssl \
    autoconf \
    bison \
    swig \
    glib2 \
    s3cmd \
    portaudio \
    mpg123 \
    screen \
    flac \
    curl

# upgrade virtualenv to latest from pypi
sudo pip2 install --upgrade virtualenv
