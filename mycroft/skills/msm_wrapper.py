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
"""Common logic for instantiating the Mycroft Skills Manager.

The Mycroft Skills Manager (MSM) does a lot of interactions with git.  The
more skills that are installed on a device, the longer these interactions
take.  This is especially true at boot time when MSM is instantiated
frequently.  To improve performance, the MSM instance is cached.
"""
from collections import namedtuple
from functools import lru_cache
from os import path, makedirs

from msm import MycroftSkillsManager, SkillRepo

from mycroft.util.combo_lock import ComboLock
from mycroft.util.log import LOG

MsmConfig = namedtuple(
    'MsmConfig',
    [
        'platform',
        'repo_branch',
        'repo_cache',
        'repo_url',
        'skills_dir',
        'versioned'
    ]
)


def _init_msm_lock():
    msm_lock = None
    try:
        msm_lock = ComboLock('/tmp/mycroft-msm.lck')
        LOG.debug('mycroft-msm combo lock instantiated')
    except Exception:
        LOG.exception('Failed to create msm lock!')

    return msm_lock


def build_msm_config(device_config: dict) -> MsmConfig:
    """Extract from the device configs values needed to instantiate MSM

    Why not just pass the device_config to the create_msm function, you ask?
    Rationale is that the create_msm function is cached.  The lru_cached
    decorator will instantiate MSM anew each time it is called with a different
    configuration argument.  Calling this function before create_msm will
    ensure that changes to configs not related to MSM will not result in new
    instances of MSM being created.
    """
    msm_config = device_config['skills']['msm']
    msm_repo_config = msm_config['repo']
    enclosure_config = device_config['enclosure']
    data_dir = path.expanduser(device_config['data_dir'])

    return MsmConfig(
        platform=enclosure_config.get('platform', 'default'),
        repo_branch=msm_repo_config['branch'],
        repo_cache=path.join(data_dir, msm_repo_config['cache']),
        repo_url=msm_repo_config['url'],
        skills_dir=path.join(data_dir, msm_config['directory']),
        versioned=msm_config['versioned']
    )


@lru_cache()
def create_msm(msm_config: MsmConfig) -> MycroftSkillsManager:
    """Returns an instantiated MSM object.

    This function is cached because it can take as long as 15 seconds to
    instantiate MSM.  Caching the instance improves performance significantly,
    especially during the boot sequence when this function is called multiple
    times.
    """
    msm_lock = _init_msm_lock()
    LOG.info('Acquiring lock to instantiate MSM')
    with msm_lock:
        if not path.exists(msm_config.skills_dir):
            makedirs(msm_config.skills_dir)

        msm_skill_repo = SkillRepo(
            msm_config.repo_cache,
            msm_config.repo_url,
            msm_config.repo_branch
        )
        msm_instance = MycroftSkillsManager(
            platform=msm_config.platform,
            skills_dir=msm_config.skills_dir,
            repo=msm_skill_repo,
            versioned=msm_config.versioned
        )
    LOG.info('Releasing MSM instantiation lock.')

    return msm_instance
