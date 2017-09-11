#!/usr/bin/env bash

if [ -z "$WORKON_HOME" ]; then
    VIRTUALENV_ROOT=${VIRTUALENV_ROOT:-"${HOME}/.virtualenvs/mycroft"}
else
    VIRTUALENV_ROOT="$WORKON_HOME/mycroft"
fi

source "${VIRTUALENV_ROOT}/bin/activate"
easy_install pip==7.1.2
pip install --upgrade virtualenv
pip install -r requirements.txt
