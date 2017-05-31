#!/usr/bin/env bash
# exit on any error

#STILL UNDER CONSTRUCTION
set -Ee

PEDATIOUS_DIR=pedatious
CORES=$(nproc)
PEDATIOUS_VERSION=0.1

# for ubuntu precise in travis, that does not provide pkg-config:
pkg-config --exists icu-i18n || export CFLAGS="$CFLAGS -I/usr/include/x86_64-linux-gnu"
pkg-config --exists icu-i18n || export LDFLAGS="$LDFLAGS -licui18n -licuuc -licudata"


#install pre-reqs for building
sudo apt-get install python3 ninja-build build-essential \
    && pip3 install --user meson

# download and install pedatious
if [ ! -d ${PEDATIOUS_DIR} ]; then
    git clone --branch ${PEDATIOUS_VERSION} https://github.com/MycroftAI/pedatious.git
    cd ${PEDATIOUS_DIR}
    make -j$CORES
else
    # ensure pedatious is up to date
    cd ${PEDATIOUS_DIR}
    make clean 2> /dev/null || true
    git remote add all-branches https://github.com/mycroftai/pedatious/ 2> /dev/null || true
    git fetch --all --tags --prune
    git checkout tags/${PEDATIOUS_VERSION}
    make clean
    make -j$CORES
    make install
fi