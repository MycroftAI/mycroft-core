#!/usr/bin/env bash

sudo pacman -S \
    git \
    python \
    python-pip \
    python-setuptools \
    python-virtualenv \
    python-gobject \
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
    curl

# upgrade virtualenv to latest from pypi
sudo pip install --upgrade virtualenv
