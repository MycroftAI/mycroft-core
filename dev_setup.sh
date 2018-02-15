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

show_help() {
        echo "dev_setup.sh: Mycroft development environment setup"
        echo "Usage: dev_setup.sh [options]"
        echo
        echo "Options:"
        echo "    -r, --allow-root  Allow to be run as root (e.g. sudo)"
        echo "    -sm               Skip building mimic"
        echo "    -h, --help        Show this message"
        echo
        echo "This will prepare your environment for running the mycroft-core"
	echo "services. Normally this should be run as a normal user,"
	echo "not as root/sudo."
}

opt_skipmimic=false
opt_allowroot=false

for var in "$@"
do
    if [[ ${var} == "-h" ]] || [[ ${var} == "--help" ]] ; then
        show_help
        exit 0
    fi

    if [[ ${var} == "-r" ]] || [[ ${var} == "--allow-root" ]] ; then
        opt_allowroot=true
    fi

    if [[ ${var} == "-sm" ]] ; then
        opt_skipmimic=true
    fi
done

if [ $(id -u) -eq 0 ] && [ "${opt_allowroot}" != true ] ; then
  echo "This script should not be run as root or with sudo."
  echo "To force, rerun with --allow-root"
  exit 1
fi

found_exe() {
    hash "$1" 2>/dev/null
}

install_deps() {
    echo "Installing packages..."
    if found_exe sudo; then
        SUDO=sudo
    fi

    if found_exe apt-get; then
        $SUDO apt-get install -y git python python-dev python-setuptools python-virtualenv python-gobject-dev virtualenvwrapper libtool libffi-dev libssl-dev autoconf automake bison swig libglib2.0-dev s3cmd portaudio19-dev mpg123 screen flac curl libicu-dev pkg-config automake libjpeg-dev libfann-dev build-essential jq
    elif found_exe pacman; then
        $SUDO pacman -S --needed --noconfirm git python2 python2-pip python2-setuptools python2-virtualenv python2-gobject python-virtualenvwrapper libtool libffi openssl autoconf bison swig glib2 s3cmd portaudio mpg123 screen flac curl pkg-config icu automake libjpeg-turbo base-devel jq
        pacman -Qs "^libfann$" &> /dev/null || (
            git clone  https://aur.archlinux.org/libfann.git
            cd libfann
            makepkg -srci --noconfirm
            cd ..
            rm -rf libfann
        )
    elif found_exe dnf; then
        $SUDO dnf install -y git python python-devel python-pip python-setuptools python-virtualenv pygobject2-devel python-virtualenvwrapper libtool libffi-devel openssl-devel autoconf bison swig glib2-devel s3cmd portaudio-devel mpg123 mpg123-plugins-pulseaudio screen curl pkgconfig libicu-devel automake libjpeg-turbo-devel fann-devel gcc-c++ redhat-rpm-config jq
    else
        if found_exe tput; then
			green="$(tput setaf 2)"
			blue="$(tput setaf 4)"
			reset="$(tput sgr0)"
    	fi
    	echo
        echo "${green}Could not find package manager"
        echo "${green}Make sure to manually install:${blue} git python 2 python-setuptools python-virtualenv pygobject virtualenvwrapper libtool libffi openssl autoconf bison swig glib2.0 s3cmd portaudio19 mpg123 flac curl fann g++"
        echo $reset
    fi
}

install_deps

# Configure to use the standard commit template for
# this repo only.
git config commit.template .gitmessage

TOP=$(cd $(dirname $0) && pwd -L)

if [ -z "$WORKON_HOME" ]; then
    VIRTUALENV_ROOT=${VIRTUALENV_ROOT:-"${HOME}/.virtualenvs/mycroft"}
else
    VIRTUALENV_ROOT="$WORKON_HOME/mycroft"
fi

# Check whether to build mimic (it takes a really long time!)
build_mimic='y'
if [[ ${opt_skipmimic} == true ]] ; then
  build_mimic='n'
else
  # first, look for a build of mimic in the folder
  has_mimic=""
  if [[ -f ${TOP}/mimic/bin/mimic ]] ; then
      has_mimic=$( ${TOP}/mimic/bin/mimic -lv | grep Voice )
  fi

  # in not, check the system path
  if [ "$has_mimic" = "" ] ; then
    if [ -x "$(command -v mimic)" ]; then
      has_mimic="$( mimic -lv | grep Voice )"
    fi
  fi

  if ! [ "$has_mimic" == "" ] ; then
    echo "Mimic is installed. Press 'y' to rebuild mimic, any other key to skip."
    read -n1 build_mimic
  fi
fi

# create virtualenv, consistent with virtualenv-wrapper conventions
if [ ! -d "${VIRTUALENV_ROOT}" ]; then
   mkdir -p $(dirname "${VIRTUALENV_ROOT}")
  virtualenv -p python2.7 "${VIRTUALENV_ROOT}"
fi
source "${VIRTUALENV_ROOT}/bin/activate"
cd "${TOP}"
easy_install pip==9.0.1 # force version of pip
pip install --upgrade virtualenv

# Add mycroft-core to the virtualenv path
# (This is equivalent to typing 'add2virtualenv $TOP', except
# you can't invoke that shell function from inside a script)
VENV_PATH_FILE="${VIRTUALENV_ROOT}/lib/python2.7/site-packages/_virtualenv_path_extensions.pth"
if [ ! -f "$VENV_PATH_FILE" ] ; then
    echo "import sys; sys.__plen = len(sys.path)" > "$VENV_PATH_FILE" || return 1
    echo "import sys; new=sys.path[sys.__plen:]; del sys.path[sys.__plen:]; p=getattr(sys,'__egginsert',0); sys.path[p:p]=new; sys.__egginsert = p+len(new)" >> "$VENV_PATH_FILE" || return 1
fi

if ! grep -q "mycroft-core" $VENV_PATH_FILE; then
   echo "Adding mycroft-core to virtualenv path"
   sed -i.tmp '1 a\
'"$TOP"'
' "${VENV_PATH_FILE}"
fi

# install requirements (except pocketsphinx)
# removing the pip2 explicit usage here for consistency with the above use.

if ! pip install -r requirements.txt; then
    echo "Warning: Failed to install all requirements. Continue? y/N"
    read -n1 continue
    if [[ "$continue" != "y" ]] ; then
        exit 1
    fi
fi

SYSMEM=$(free|awk '/^Mem:/{print $2}')
MAXCORES=$(($SYSMEM / 512000))
CORES=$(nproc)

if [[ ${MAXCORES} -lt ${CORES} ]]; then
  CORES=${MAXCORES}
fi
echo "Building with $CORES cores."

#build and install pocketsphinx
#cd ${TOP}
#${TOP}/scripts/install-pocketsphinx.sh -q
#build and install mimic
cd "${TOP}"

if [[ "$build_mimic" == 'y' ]] || [[ "$build_mimic" == 'Y' ]]; then
  echo "WARNING: The following can take a long time to run!"
  "${TOP}/scripts/install-mimic.sh" " ${CORES}"
else
  echo "Skipping mimic build."
fi

# install pygtk for desktop_launcher skill
"${TOP}/scripts/install-pygtk.sh" " ${CORES}"

# set permissions for common scripts
chmod +x start-mycroft.sh
chmod +x stop-mycroft.sh

md5sum requirements.txt dev_setup.sh > .installed
