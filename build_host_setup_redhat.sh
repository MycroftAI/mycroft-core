#!/usr/bin/env bash

sudo yum -y install epel-release http://repo.okay.com.mx/centos/7/x86_64/release/okay-release-1-1.noarch.rpm

sudo yum install -y \
    git \
    python \
    python-devel \
    python-setuptools \
    python-virtualenv \
    pygobject2 \
    virtualenvwrapper \
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
    screen \
    flac \
    curl

