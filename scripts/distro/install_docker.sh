#!/usr/bin/env bash
#Docker doesn't use sudo so need one without sudo for automation of image.

apt-get install -y \
    git \
    python \
    python-dev \
    python-setuptools \
    python-virtualenv \
    python-gobject-dev \
    virtualenvwrapper \
    libtool \
    libffi-dev \
    libssl-dev \
    autoconf \
    automake \
    bison \
    swig \
    libglib2.0-dev \
    s3cmd \
    portaudio19-dev \
    mpg123 \
    screen \
    flac \
    curl \
    libicu-dev \
    pkg-config \
    automake
