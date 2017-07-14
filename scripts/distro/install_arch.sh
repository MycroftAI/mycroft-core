#!/usr/bin/env bash

sudo pacman -S --needed \
    git \
    python2 \
    python2-pip \
    python2-setuptools \
    python2-virtualenv \
    python2-gobject \
    python-virtualenvwrapper \
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
    curl \
    pkg-config \
    icu \
    automake

# upgrade virtualenv to latest from pypi
sudo pip2 install --upgrade virtualenv
