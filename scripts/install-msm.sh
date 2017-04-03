#!/usr/bin/env bash
# exit on any error
set -Ee
rm -rf msm
git clone https://github.com/MycroftAI/msm.git msm
chmod +x msm/msm
sudo mkdir -p /opt/mycroft/skills
sudo chown $USER:$USER /opt/mycroft/skills
