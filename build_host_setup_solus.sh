#!/usr/bin/env bash

sudo eopkg it -cy system.devel
sudo eopkg it \
    git \
#    python \
    pip \
    python-setuptools \
    virtualenv \
#    python-gobject \
    virtualenvwrapper \
#    libtool \
#    libffi \
#    openssl \
#    autoconf \
#    bison \
#    swig \
#    glib2 \
    alsa-lib-devel \
#    portaudio \
    portaudio-devel \
    mpg123 \
    screen \
#    libflac \
#    curl

# upgrade virtualenv to latest from pypi
sudo pip install --upgrade virtualenv
sudo pip install s3cmd
