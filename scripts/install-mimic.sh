#!/usr/bin/env bash
# exit on any error
set -Ee

MIMIC_DIR=mimic
CORES=$(nproc)
MIMIC_VERSION=1.2.0

# download and install mimic
if [ ! -d ${MIMIC_DIR} ]; then
    git clone --branch ${MIMIC_VERSION} https://github.com/MycroftAI/mimic.git
    cd ${MIMIC_DIR}
    ./autogen
    ./configure --with-audio=alsa --enable-shared
    make #-j$CORES
else
    # ensure mimic is up to date
    cd ${MIMIC_DIR}
    git pull
    make clean
    ./autogen
    ./configure --with-audio=alsa --enable-shared
    make #-j$CORES
fi
