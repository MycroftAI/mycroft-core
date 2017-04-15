#!/usr/bin/env bash

SKILLS_DIR='/opt/mycroft/skills'
# exit on any error
set -Ee
chmod +x msm/msm

if [[ ${IS_TRAVIS} != true ]]; then
    if [ ! -d ${SKILLS_DIR} ]; then
        echo "Create /opt/mycroft/skills"
        sudo mkdir -p ${SKILLS_DIR}
    fi

    if [ ! -w ${SKILLS_DIR} ]; then
        echo "Changing ownsership of /opt/mycroft/skills"
        sudo chown $USER:$USER ${SKILLS_DIR}
    fi
fi
