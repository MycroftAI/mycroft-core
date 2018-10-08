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

######################################################
# @author sean.fitzgerald (aka clusterfudge)
#
# The purpose of this script is to create a self-
# contained development environment using
# virtualenv for python dependency sandboxing.
# This script will create a virtualenv (using the
# conventions set by virtualenv-wrapper for
# location and naming) and install the requirements
# laid out in requirements.txt, pocketsphinx, and
# pygtk into the virtualenv. Mimic will be
# installed and built from source inside the local
# checkout.
#
# The goal of this script is to create a development
# environment in user space that is fully functional.
# It is expected (and even encouraged) for a developer
# to work on multiple projects concurrently, and a
# good OSS citizen respects that and does not pollute
# a developers workspace with it's own dependencies
# (as much as possible).
# </endRant>
######################################################

# exit on any error
set -Ee

cd $(dirname $0)
TOP=$( pwd -L )

function show_help() {
    echo "dev_setup.sh: Mycroft development environment setup"
    echo "Usage: dev_setup.sh [options]"
    echo
    echo "Options:"
    echo "    -r, --allow-root  Allow to be run as root (e.g. sudo)"
    echo "    -fm               Force mimic build"
    echo "    -h, --help        Show this message"
    echo
    echo "This will prepare your environment for running the mycroft-core"
    echo "services. Normally this should be run as a normal user,"
    echo "not as root/sudo."
}

opt_forcemimicbuild=false
opt_allowroot=false

for var in "$@" ; do
    if [[ ${var} == "-h" ]] || [[ ${var} == "--help" ]] ; then
        show_help
        exit 0
    fi

    if [[ ${var} == "-r" ]] || [[ ${var} == "--allow-root" ]] ; then
        opt_allowroot=true
    fi

    if [[ ${var} == "-fm" ]] ; then
        opt_forcemimicbuild=true
    fi
done

if [ $(id -u) -eq 0 ] && [ "${opt_allowroot}" != true ] ; then
    echo "This script should not be run as root or with sudo."
    echo "To force, rerun with --allow-root"
    exit 1
fi

# TODO: Create a setup wizard that guides the user through some decisions
# if [ ! -f .dev_opts.json ] ; then
    # E.g.:
    #  * Run on 'master' or on 'dev'?  Most users probably want 'master'
    #  * Auto-update?  When on, it will pull and run dev_setup automatically
    #  * Pull down mimic source?  Most will be happy with just the package
    #  * Add mycroft-core/bin to the .bashrc PATH?

    # from Picroft's wizard:
    #   echo '{"use_branch":"master", "auto_update": true}' > .dev_opts.json
    # or
    #   echo '{"use_branch":"dev", "auto_update": false}' > .dev_opts.json
# fi

function found_exe() {
    hash "$1" 2>/dev/null
}

function install_deps() {
    echo "Installing packages..."
    if found_exe sudo ; then
        SUDO=sudo
    else
        echo "This script requires \"sudo\" to install system packages. Please install it, then re-run this script."
        exit 1
    fi

    if found_exe zypper ; then
        $SUDO zypper install -y git python3 python3-devel libtool libffi-devel libopenssl-devel autoconf automake bison swig portaudio-devel mpg123 flac curl libicu-devel pkg-config libjpeg-devel libfann-devel python3-curses pulseaudio
        $SUDO zypper install -y -t pattern devel_C_C++
    elif found_exe yum ; then
        $SUDO yum install epel-release
        $SUDO yum install -y cmake gcc-c++ git python34 python34-devel libtool libffi-devel openssl-devel autoconf automake bison swig portaudio-devel mpg123 flac curl libicu-devel python34-pkgconfig libjpeg-devel fann-devel python34-libs pulseaudio
        git clone https://github.com/libfann/fann.git
        cd fann
        cmake .
        $SUDO make install
        cd "${TOP}"
        rm -rf fann
    elif found_exe apt-get ; then
        $SUDO apt-get install -y git python3 python3-dev python-setuptools python-gobject-2-dev libtool libffi-dev libssl-dev autoconf automake bison swig libglib2.0-dev portaudio19-dev mpg123 screen flac curl libicu-dev pkg-config automake libjpeg-dev libfann-dev build-essential jq
    elif found_exe pacman; then
        $SUDO pacman -S --needed --noconfirm git python python-pip python-setuptools python-virtualenv python-gobject python-virtualenvwrapper libffi swig portaudio mpg123 screen flac curl icu libjpeg-turbo base-devel jq pulseaudio pulseaudio-alsa
        pacman -Qs "^fann$" &> /dev/null || (
            git clone  https://aur.archlinux.org/fann.git
            cd fann
            makepkg -srciA --noconfirm
            cd ..
            rm -rf fann
        )
    elif found_exe dnf ; then
        $SUDO dnf install -y git python3 python3-devel python3-pip python3-setuptools python3-virtualenv pygobject3-devel libtool libffi-devel openssl-devel autoconf bison swig glib2-devel portaudio-devel mpg123 mpg123-plugins-pulseaudio screen curl pkgconfig libicu-devel automake libjpeg-turbo-devel fann-devel gcc-c++ redhat-rpm-config jq
    else
        if found_exe tput ; then
			green="$(tput setaf 2)"
			blue="$(tput setaf 4)"
			reset="$(tput sgr0)"
    	fi
    	echo
        echo "${green}Could not find package manager"
        echo "${green}Make sure to manually install:${blue} git python 2 python-setuptools python-virtualenv pygobject virtualenvwrapper libtool libffi openssl autoconf bison swig glib2.0 portaudio19 mpg123 flac curl fann g++"
        echo $reset
    fi
}

VIRTUALENV_ROOT=${VIRTUALENV_ROOT:-"${TOP}/.venv"}

function install_venv() {
    python3 -m venv "${VIRTUALENV_ROOT}/" --without-pip
    # Force version of pip for reproducability, but there is nothing special
    # about this version.  Update whenever a new version is released and
    # verified functional.
    curl https://bootstrap.pypa.io/3.3/get-pip.py | "${VIRTUALENV_ROOT}/bin/python" - 'pip==18.0.0'
}

install_deps

# Configure to use the standard commit template for
# this repo only.
git config commit.template .gitmessage

# Check whether to build mimic (it takes a really long time!)
build_mimic="n"
if [[ ${opt_forcemimicbuild} == true ]] ; then
    build_mimic="y"
else
    # first, look for a build of mimic in the folder
    has_mimic=""
    if [[ -f ${TOP}/mimic/bin/mimic ]] ; then
        has_mimic=$( ${TOP}/mimic/bin/mimic -lv | grep Voice ) || true
    fi

    # in not, check the system path
    if [ "$has_mimic" == "" ] ; then
        if [ -x "$(command -v mimic)" ] ; then
            has_mimic="$( mimic -lv | grep Voice )" || true
        fi
    fi

    if [ "$has_mimic" == "" ]; then
        build_mimic="y"
    fi
fi

if [ ! -x "${VIRTUALENV_ROOT}/bin/activate" ] ; then
    install_venv
fi

# Start the virtual environment
source "${VIRTUALENV_ROOT}/bin/activate"
cd "${TOP}"

PYTHON=$( python -c "import sys;print('python{}.{}'.format(sys.version_info[0], sys.version_info[1]))" )

# Add mycroft-core to the virtualenv path
# (This is equivalent to typing 'add2virtualenv $TOP', except
# you can't invoke that shell function from inside a script)
VENV_PATH_FILE="${VIRTUALENV_ROOT}/lib/$PYTHON/site-packages/_virtualenv_path_extensions.pth"
if [ ! -f "$VENV_PATH_FILE" ] ; then
    echo "import sys; sys.__plen = len(sys.path)" > "$VENV_PATH_FILE" || return 1
    echo "import sys; new=sys.path[sys.__plen:]; del sys.path[sys.__plen:]; p=getattr(sys,'__egginsert',0); sys.path[p:p]=new; sys.__egginsert = p+len(new)" >> "$VENV_PATH_FILE" || return 1
fi

if ! grep -q "$TOP" $VENV_PATH_FILE ; then
    echo "Adding mycroft-core to virtualenv path"
    sed -i.tmp '1 a\
'"$TOP"'
' "${VENV_PATH_FILE}"
fi

# install required python modules
if ! pip install -r requirements.txt ; then
    echo "Warning: Failed to install all requirements. Continue? y/N"
    read -n1 continue
    if [[ "$continue" != "y" ]] ; then
        exit 1
    fi
fi

if ! pip install -r test-requirements.txt ; then
    echo "Warning test requirements wasn't installed, Note: normal operation should still work fine..."
fi

SYSMEM=$( free | awk '/^Mem:/ { print $2 }' )
MAXCORES=$(($SYSMEM / 512000))
MINCORES=1
CORES=$( nproc )

# ensure MAXCORES is > 0
if [[ ${MAXCORES} -lt 1 ]] ; then
    MAXCORES=${MINCORES}
fi

# look for positive integer
if ! [[ ${CORES} =~ ^[0-9]+$ ]] ; then
    CORES=${MINCORES}
elif [[ ${MAXCORES} -lt ${CORES} ]] ; then
    CORES=${MAXCORES}
fi

echo "Building with $CORES cores."

#build and install pocketsphinx
#cd ${TOP}
#${TOP}/scripts/install-pocketsphinx.sh -q
#build and install mimic
cd "${TOP}"

if [[ "$build_mimic" == "y" ]] || [[ "$build_mimic" == "Y" ]] ; then
    echo "WARNING: The following can take a long time to run!"
    "${TOP}/scripts/install-mimic.sh" " ${CORES}"
else
    echo "Skipping mimic build."
fi

# set permissions for common scripts
chmod +x start-mycroft.sh
chmod +x stop-mycroft.sh
chmod +x bin/mycroft-cli-client
chmod +x bin/mycroft-help
chmod +x bin/mycroft-mic-test
chmod +x bin/mycroft-msk
chmod +x bin/mycroft-msm
chmod +x bin/mycroft-pip
chmod +x bin/mycroft-say-to
chmod +x bin/mycroft-skill-testrunner
chmod +x bin/mycroft-speak

# create and set permissions for logging
if [[ ! -w /var/log/mycroft/ ]] ; then
    # Creating and setting permissions
    echo "Creating /var/log/mycroft/ directory"
    if [[ ! -d /var/log/mycroft/ ]] ; then
        sudo mkdir /var/log/mycroft/
    fi
    sudo chmod 777 /var/log/mycroft/
fi

#Store a fingerprint of setup
md5sum requirements.txt test-requirements.txt dev_setup.sh > .installed
