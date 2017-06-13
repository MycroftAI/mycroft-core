#!/usr/bin/env bash
# exit on any error

#STILL UNDER CONSTRUCTION
set -Ee

PADATIOUS_DIR=padatious
CORES=$(nproc)
PADATIOUS_VERSION=0.1

# for ubuntu precise in travis, that does not provide pkg-config:
pkg-config --exists icu-i18n || export CFLAGS="$CFLAGS -I/usr/include/x86_64-linux-gnu"
pkg-config --exists icu-i18n || export LDFLAGS="$LDFLAGS -licui18n -licuuc -licudata"


#install pre-reqs for building
sudo apt-get install python3 ninja-build build-essential \
    && pip3 install --user meson

# download and install pedatious
if [ ! -d ${PADATIOUS_DIR} ]; then
    #TODO: add versioning later
    git clone https://github.com/MycroftAI/padatious.git
    cd ${PADATIOUS_DIR}
    meson build
    cd build
    ninja clean # Optional; same as make clean
    ninja
else
    # ensure pedatious is up to date
    cd ${PADATIOUS_DIR}
    git remote add all-branches https://github.com/mycroftai/padatious/ 2> /dev/null || true
    git fetch --all --tags --prune
    #TODO: Add versioning
    meson build
    cd build
    ninja clean # Optional; same as make clean
    ninja
fi
