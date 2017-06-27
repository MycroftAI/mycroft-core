#!/usr/bin/env bash

sudo dnf install -y \
    git \
    python \
    python-devel \
    python-pip \
    python-setuptools \
    python-virtualenv \
    pygobject2-devel \
    python-virtualenvwrapper \
    libtool \
    libffi-devel \
    openssl-devel \
    autoconf \
    bison \
    swig \
    glib2-devel \
    s3cmd \
    portaudio-devel \
    mpg123 \
    mpg123-plugins-pulseaudio \
    screen \
    curl \
    pkgconfig \
    libicu-devel \
    automake

# upgrade virtualenv to latest from pypi
sudo pip install --upgrade virtualenv
