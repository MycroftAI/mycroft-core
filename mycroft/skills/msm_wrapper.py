# Copyright 2019 Mycroft AI Inc.
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
#

import os
from os.path import join, expanduser, exists

from msm import MycroftSkillsManager, SkillRepo
from mycroft.util.combo_lock import ComboLock

mycroft_msm_lock = ComboLock('/tmp/mycroft-msm.lck')


def create_msm(config):
    """ Create msm object from config. """
    msm_config = config['skills']['msm']
    repo_config = msm_config['repo']
    data_dir = expanduser(config['data_dir'])
    skills_dir = join(data_dir, msm_config['directory'])
    repo_cache = join(data_dir, repo_config['cache'])
    platform = config['enclosure'].get('platform', 'default')

    with mycroft_msm_lock:
        # Try to create the skills directory if it doesn't exist
        if not exists(skills_dir):
            os.makedirs(skills_dir)

        return MycroftSkillsManager(
            platform=platform, skills_dir=skills_dir,
            repo=SkillRepo(repo_cache, repo_config['url'],
                           repo_config['branch']),
            versioned=msm_config['versioned'])
