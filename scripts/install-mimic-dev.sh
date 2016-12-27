#!/usr/bin/env bash
# exit on any error
set -Ee

MIMIC_DIR=mimic-dev
CORES=$(nproc)

# download and install mimic
if [ ! -d ${MIMIC_DIR} ]; then
    git clone https://github.com/MycroftAI/mimic.git ${MIMIC_DIR}
    cd ${MIMIC_DIR}
    git fetch origin
    git checkout origin/development
    ./autogen.sh
    ./configure --with-audio=alsa --prefix=`pwd` --enable-shared --disable-vid_gb_ap
    make -j$CORES
    make install
else
    # ensure mimic is up to date
    cd ${MIMIC_DIR}
    make distclean
    git fetch origin
    git checkout origin/development
    ./autogen.sh
    ./configure --with-audio=alsa --prefix=`pwd` --enable-shared
    make #-j$CORES
    make install
fi
