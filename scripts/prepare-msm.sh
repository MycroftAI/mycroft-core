#!/usr/bin/env bash

mycroft_root_dir='/opt/mycroft'
skills_dir="${mycroft_root_dir}"/skills
# exit on any error
set -Ee
chmod +x msm/msm

# Determine which user is running this script
setup_user=$USER

# change ownership of ${mycroft_root_dir} to ${setup_user } recursively 
function change_ownership {
    echo "Changing ownership of" ${mycroft_root_dir} "to user:" ${setup_user} "with group:" ${setup_user}
            sudo chown -Rvf ${setup_user}:${setup_user} ${mycroft_root_dir}
}


if [[ ${IS_TRAVIS} != true ]]; then
    if [ ! -d ${skills_dir} ]; then
        echo "Create /opt/mycroft/skills"
        sudo mkdir -p ${skills_dir}
	change_ownership
    fi

    if [ ! -w ${SKILLS_DIR} ]; then
        change_ownership
    fi
fi

# fix ownership of ${mycroft_root_dir} if it is not owned by the ${setup_user}
if [[ `stat -c "%U:%G" /opt/mycroft` != "${setup_user}:${setup_user}" ]]; then
    change_ownership
fi
