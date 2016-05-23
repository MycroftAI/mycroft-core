#!/usr/bin/env bash

sudo apt-get install -y \
    git \
    python \
    python-dev \
    python-virtualenv \
    python-gobject-dev \
    virtualenvwrapper \
    libtool \
    libffi-dev \
    libssl-dev \
    autoconf \
    bison \
    swig \
    libglib2.0-dev \
    s3cmd \
    portaudio19-dev \
    mpg123

# upgrade virtualenv to latest from pypi
sudo easy_install --upgrade virtualenv
