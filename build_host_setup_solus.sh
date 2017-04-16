#!/usr/bin/env bash

sudo eopkg it -y -c system.devel \
    git \
    pip \
    python-setuptools \
    virtualenv \
    virtualenvwrapper \
    alsa-lib-devel \
    portaudio-devel \
    mpg123 \
    screen \

# upgrade virtualenv to latest from pypi
sudo pip install --upgrade virtualenv
sudo pip install s3cmd
