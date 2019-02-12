#!/usr/bin/env bash
#
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
##########################################################################

# exit on any error
set -Ee

cd $(dirname $0)
TOP=$( pwd -L )

function show_help() {
    echo "
Usage: dev_setup.sh [options]
Prepare your environment for running the mycroft-core services.

Options:
    -h, --help              Show this message
    -fm                     Force mimic build
    -n, --no-error          Do not exit on error (use with caution)
    -p arg, --python arg    Sets the python version to use
    -r, --allow-root        Allow to be run as root (e.g. sudo)
    -sm                     Skip mimic build
"
}

# Parse the command line
opt_forcemimicbuild=false
opt_allowroot=false
opt_skipmimicbuild=false
opt_python=python3
param=""

for var in "$@" ; do
    # Check if parameter should be read
    if [[ ${param} == "python" ]] ; then
        opt_python=${var}
        param=""
        continue
    fi

    # Check for options
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
    if [[ ${var} == "-n" ]] || [[ ${var} == "--no-error" ]] ; then
        # Do NOT exit on errors
	set +Ee
    fi
    if [[ ${var} == "-sm" ]] ; then
        opt_skipmimicbuild=true
    fi
    if [[ ${var} == "-p" ]] || [[ ${var} == "--python" ]] ; then
        param="python"
    fi
done

if [ $(id -u) -eq 0 ] && [ "${opt_allowroot}" != true ] ; then
    echo "This script should not be run as root or with sudo."
    echo "If you really need to for this, rerun with --allow-root"
    exit 1
fi


function found_exe() {
    hash "$1" 2>/dev/null
}


if found_exe sudo ; then
    SUDO=sudo
elif [ "${opt_allowroot}" != true ]; then
    echo "This script requires \"sudo\" to install system packages. Please install it, then re-run this script."
    exit 1
fi


function get_YN() {
    # Loop until the user hits the Y or the N key
    echo -e -n "Choice [${CYAN}Y${RESET}/${CYAN}N${RESET}]: "
    while true; do
        read -N1 -s key
        case $key in
        [Yy])
            return 0
            ;;
        [Nn])
            return 1
            ;;
        esac
    done
}

if found_exe tput ; then
    GREEN="$(tput setaf 2)"
    BLUE="$(tput setaf 4)"
    CYAN="$(tput setaf 6)"
    YELLOW="$(tput setaf 3)"
    RESET="$(tput sgr0)"
    HIGHLIGHT=${YELLOW}
fi

# Run a setup wizard the very first time that guides the user through some decisions
if [[ ! -f .dev_opts.json ]] && [[ ${IS_TRAVIS} == "" ]] ; then
    echo "
${CYAN}                    Welcome to Mycroft!  ${RESET}"
    sleep 0.5
    echo "
This script is designed to make working with Mycroft easy.  During this
first run of dev_setup we will ask you a few questions to help setup
your environment."
    sleep 0.5
    echo "
Do you want to run on 'master' or against a dev branch?  Unless you are
a developer modifying mycroft-core itself, you should run on the
'master' branch.  It is updated bi-weekly with a stable release.
  Y)es, run on the stable 'master' branch
  N)o, I want to run unstable branches"
    if get_YN ; then
        echo -e "${HIGHLIGHT} Y - using 'master' branch ${RESET}"
        branch=master
        git checkout ${branch}
    else
        echo -e "${HIGHLIGHT} N - using an unstable branch ${RESET}"
        branch=dev
    fi

    sleep 0.5
    echo "
Mycroft is actively developed and constantly evolving.  It is recommended
that you update regularly.  Would you like to automatically update
whenever launching Mycroft?  This is highly recommended, especially for
those running against the 'master' branch.
  Y)es, automatically check for updates
  N)o, I will be responsible for keeping Mycroft updated."
    if get_YN ; then
        echo -e "${HIGHLIGHT} Y - update automatically ${RESET}"
        autoupdate=true
    else
        echo -e "${HIGHLIGHT} N - update manually using 'git pull' ${RESET}"
        autoupdate=false
    fi

    #  Pull down mimic source?  Most will be happy with just the package
    if [[ ${opt_forcemimicbuild} == false && ${opt_skipmimicbuild} == false ]] ; then
        sleep 0.5
        echo "
Mycroft uses its Mimic technology to speak to you.  Mimic can run both
locally and from a server.  The local Mimic is more robotic, but always
available regardless of network connectivity.  It will act as a fallback
if unable to contact the Mimic server.

However, building the local Mimic is time consuming -- it can take hours
on slower machines.  This can be skipped, but Mycroft will be unable to
talk if you lose network connectivity.  Would you like to build Mimic
locally?"
        if get_YN ; then
            echo -e "${HIGHLIGHT} Y - Mimic will be built ${RESET}"
        else
            echo -e "${HIGHLIGHT} N - skip Mimic build ${RESET}"
            opt_skipmimicbuild=true
        fi
    fi

    echo
    # Add mycroft-core/bin to the .bashrc PATH?
    sleep 0.5
    echo "
There are several Mycroft helper commands in the bin folder.  These
can be added to your system PATH, making it simpler to use Mycroft.
Would you like this to be added to your PATH in the .profile?"
    if get_YN ; then
        echo -e "${HIGHLIGHT} Y - Adding Mycroft commands to your PATH ${RESET}"

        if [ ! -f ~/.profile_mycroft ] ; then
            # Only add the following to the .profile if .profile_mycroft
            # doesn't exist, indicating this script has not been run before
            echo '' >> ~/.profile
            echo '# include Mycroft commands' >> ~/.profile
            echo 'source ~/.profile_mycroft' >> ~/.profile
        fi

        echo "
# WARNING: This file may be replaced in future, do not customize.
# set path so it includes Mycroft utilities
if [ -d \"${TOP}/bin\" ] ; then
    PATH=\"\$PATH:${TOP}/bin\"
fi" > ~/.profile_mycroft
        echo -e "Type ${CYAN}mycroft-help${RESET} to see available commands."
    else
        echo -e "${HIGHLIGHT} N - PATH left unchanged ${RESET}"
    fi

    # Create a link to the 'skills' folder.
    sleep 0.5
    echo
    echo "The standard location for Mycroft skills is under /opt/mycroft/skills."
    if [[ ! -d /opt/mycroft/skills ]] ; then
        echo "This script will create that folder for you.  This requires sudo"
        echo "permission and might ask you for a password..."
        $SUDO mkdir -p /opt/mycroft/skills
        $SUDO chown -R $USER:$USER /opt/mycroft
        echo "Created!"
    fi
    if [[ ! -d skills ]] ; then
        ln -s /opt/mycroft/skills skills
        echo "For convenience, a soft link has been created called 'skills' which leads"
        echo "to /opt/mycroft/skills."
    fi

    # Save options
    echo '{"use_branch": "'${branch}'", "auto_update": '${autoupdate}'}' > .dev_opts.json

    echo
    echo "Interactive portion complete, now installing dependencies..."
    echo
    sleep 5
fi



function os_is() {
    [[ $(grep "^ID=" /etc/os-release | awk -F'=' '/^ID/ {print $2}' | sed 's/\"//g') == $1 ]]
}

function redhat_common_install() {
    $SUDO yum install -y cmake gcc-c++ git python34 python34-devel libtool libffi-devel openssl-devel autoconf automake bison swig portaudio-devel mpg123 flac curl libicu-devel python34-pkgconfig libjpeg-devel fann-devel python34-libs pulseaudio
    git clone https://github.com/libfann/fann.git
    cd fann
    git checkout b211dc3db3a6a2540a34fbe8995bf2df63fc9939
    cmake .
    $SUDO make install
    cd "${TOP}"
    rm -rf fann

}

function install_deps() {
    echo "Installing packages..."
    if found_exe zypper ; then
        # OpenSUSE
        $SUDO zypper install -y git python3 python3-devel libtool libffi-devel libopenssl-devel autoconf automake bison swig portaudio-devel mpg123 flac curl libicu-devel pkg-config libjpeg-devel libfann-devel python3-curses pulseaudio
        $SUDO zypper install -y -t pattern devel_C_C++
    elif found_exe yum && os_is centos ; then
        # CentOS
        $SUDO yum install epel-release
        redhat_common_install
    elif found_exe yum && os_is rhel ; then
        # Redhat Enterprise Linux
        $SUDO yum install -y wget
        wget https://dl.fedoraproject.org/pub/epel/epel-release-latest-7.noarch.rpm
        $SUDO yum install -y epel-release-latest-7.noarch.rpm
        rm epel-release-latest-7.noarch.rpm
        redhat_common_install
    elif found_exe apt-get ; then
        # Debian / Ubuntu
        $SUDO apt-get install -y git python3 python3-dev python-setuptools python-gobject-2-dev libtool libffi-dev libssl-dev autoconf automake bison swig libglib2.0-dev portaudio19-dev mpg123 screen flac curl libicu-dev pkg-config automake libjpeg-dev libfann-dev build-essential jq
    elif found_exe pacman; then
        # Arch Linux
        $SUDO pacman -S --needed --noconfirm git python python-pip python-setuptools python-virtualenv python-gobject python-virtualenvwrapper libffi swig portaudio mpg123 screen flac curl icu libjpeg-turbo base-devel jq pulseaudio pulseaudio-alsa
        pacman -Qs "^fann$" &> /dev/null || (
            git clone  https://aur.archlinux.org/fann.git
            cd fann
            makepkg -srciA --noconfirm
            cd ..
            rm -rf fann
        )
    elif found_exe dnf ; then
        # Fedora
        $SUDO dnf install -y git python3 python3-devel python3-pip python3-setuptools python3-virtualenv pygobject3-devel libtool libffi-devel openssl-devel autoconf bison swig glib2-devel portaudio-devel mpg123 mpg123-plugins-pulseaudio screen curl pkgconfig libicu-devel automake libjpeg-turbo-devel fann-devel gcc-c++ redhat-rpm-config jq
    else
    	echo
        echo "${GREEN}Could not find package manager"
        echo "${GREEN}Make sure to manually install:${BLUE} git python 2 python-setuptools python-virtualenv pygobject virtualenvwrapper libtool libffi openssl autoconf bison swig glib2.0 portaudio19 mpg123 flac curl fann g++"
        echo ${RESET}
    fi
}

VIRTUALENV_ROOT=${VIRTUALENV_ROOT:-"${TOP}/.venv"}

function install_venv() {
    ${opt_python} -m venv "${VIRTUALENV_ROOT}/" --without-pip
    # Force version of pip for reproducability, but there is nothing special
    # about this version.  Update whenever a new version is released and
    # verified functional.
    curl https://bootstrap.pypa.io/3.3/get-pip.py | "${VIRTUALENV_ROOT}/bin/python" - 'pip==18.0.0'
    # Function status depending on if pip exists
    [ -x "${VIRTUALENV_ROOT}/bin/pip" ]
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
        if [[ ${opt_skipmimicbuild} == true ]] ; then
            build_mimic="n"
        else
            build_mimic="y"
        fi
    fi
fi

if [ ! -x "${VIRTUALENV_ROOT}/bin/activate" ] ; then
    if ! install_venv ; then
        echo "Failed to set up virtualenv for mycroft, exiting setup."
        exit 1
    fi
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
        $SUDO mkdir /var/log/mycroft/
    fi
    $SUDO chmod 777 /var/log/mycroft/
fi

#Store a fingerprint of setup
md5sum requirements.txt test-requirements.txt dev_setup.sh > .installed
