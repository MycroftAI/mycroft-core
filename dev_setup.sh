#!/usr/bin/env bash
# exit on any error
set -Ee

TOP=$(cd $(dirname $0) && pwd -L)
VIRTUALENV_ROOT=${VIRTUALENV_ROOT:-"${HOME}/.virtualenvs/mycroft"}

# create virtualenv, consistent with virtualenv-wrapper conventions
if [ ! -d ${VIRTUALENV_ROOT} ]; then
  mkdir -p $(dirname ${VIRTUALENV_ROOT})
  virtualenv ${VIRTUALENV_ROOT}
fi
source ${VIRTUALENV_ROOT}/bin/activate
cd ${TOP}
easy_install pip==7.1.2 # force version of pip

# install requirements (except pocketsphinx)
pip install -r requirements.txt --trusted-host pypi.mycroft.team

# clone pocketsphinx-python at HEAD (fix to a constant version later)
if [ ! -d ${TOP}/pocketsphinx-python ]; then
  # build sphinxbase and pocketsphinx if we haven't already
  git clone --recursive https://github.com/cmusphinx/pocketsphinx-python
  cd ${TOP}/pocketsphinx-python/sphinxbase
  ./autogen.sh
  ./configure
  make
  cd ${TOP}/pocketsphinx-python/pocketsphinx
  ./autogen.sh
  ./configure
  make
fi

# build and install pocketsphinx python bindings
cd ${TOP}/pocketsphinx-python
python setup.py install

#build and install mimic
cd ${TOP}
${TOP}/install-mimic.sh

# install pygtk for desktop_launcher skill
${TOP}/install-pygtk.sh
