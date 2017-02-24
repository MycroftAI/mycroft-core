#!/usr/bin/env bash
# exit on any error
set -Ee

MIMIC_DIR=mimic
CORES=$(nproc)
MIMIC_VERSION=1.2.0.1

# for ubuntu precise in travis, that does not provide pkg-config:
pkg-config --exists icu-i18n || export CFLAGS="$CFLAGS -I/usr/include/x86_64-linux-gnu"
pkg-config --exists icu-i18n || export LDFLAGS="$LDFLAGS -licui18n -licuuc -licudata"

# download and install mimic
if [ ! -d ${MIMIC_DIR} ]; then
    git clone --branch ${MIMIC_VERSION} https://github.com/MycroftAI/mimic.git
    cd ${MIMIC_DIR}
    ./autogen.sh
    ./configure --with-audio=alsa --enable-shared --prefix=$(pwd)
    make -j$CORES
    make install
else
    # ensure mimic is up to date
    cd ${MIMIC_DIR}
    git pull
    ./autogen.sh
    ./configure --with-audio=alsa --enable-shared --prefix=$(pwd)
    make clean
    make -j$CORES
    make install
fi
