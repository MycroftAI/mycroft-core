#!/usr/bin/env bash

# Copyright 2017 Mycroft AI Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# exit on any error
set -Ee

#TOP="."


function enable_local() {
    sed -i 's/from pocketsphinx.pocketsphinx import Decoder/from pocketsphinx import Decoder/g' mycroft/client/speech/local_recognizer.py
}

function disable_local() {
    sed -i 's/from pocketsphinx import Decoder/from pocketsphinx.pocketsphinx import Decoder/g' mycroft/client/speech/local_recognizer.py
}

function install_pocketsphinx() {
    # clone pocketsphinx-python at HEAD (fix to a constant version later)
    if [ ! -d ${TOP}/pocketsphinx-python ] ; then
        # build sphinxbase and pocketsphinx if we haven't already
        git clone --recursive https://github.com/cmusphinx/pocketsphinx-python
        pushd ./pocketsphinx-python/sphinxbase
        ./autogen.sh
        ./configure
        make -j$CORES
        popd
        pushd ./pocketsphinx-python/pocketsphinx
        ./autogen.sh
        ./configure
        make -j$CORES
        popd
    fi

    # build and install pocketsphinx python bindings
    cd ${TOP}/pocketsphinx-python
    python setup.py install
}

if [ "$1" = "-q" ] ; then
    enable_local
    install_pocketsphinx
    exit 0
fi

echo "This script will checkout, compile, and install pocketsphinx locally if the debian package python-pocketsphinx is not available"

PS3='Please enter your choice: '
options=("Enable local checkout, compile and install" "Disable local checkout and exit" "Do nothing and quit")
select opt in "${options[@]}" ; do
    case $opt in
        "Enable local checkout, compile and install")
            echo "you chose choice 1"
            enable_local
            install_pocketsphinx
            ;;
        "Disable local checkout and exit")
            echo "you chose choice 2"
            disable_local
            exit 0
            ;;
        "Do nothing and quit")
            echo "you chose choice 3"
            exit 0
            ;;
        *)
	    echo invalid option
	    ;;
    esac
done
