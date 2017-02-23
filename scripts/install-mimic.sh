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
    ./autogen.sh
    ./configure --with-audio=alsa --enable-shared --prefix=$(pwd)
    make -j$CORES CFLAGS=-D_DEFAULT_SOURCE $(CFLAGS)
else
    # ensure mimic is up to date
    cd ${MIMIC_DIR}
    git pull
    ./autogen.sh
    ./configure --with-audio=alsa --enable-shared --prefix=$(pwd)
    make clean
    make -j$CORES CFLAGS=-D_DEFAULT_SOURCE $(CFLAGS)
fi
