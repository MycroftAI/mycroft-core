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

"""
NOTE: this is dead code! do not use!
This file is only present to ensure backwards compatibility
in case someone is importing from here
This is only meant for 3rd party code expecting ovos-core
to be a drop in replacement for mycroft-core
"""

from collections import namedtuple
from os import path, makedirs

from combo_lock import ComboLock
from mycroft.util.log import LOG
from mycroft.util.file_utils import get_temp_path
from mycroft.skills.skill_loader import get_default_skills_directory

from mock_msm import \
    MycroftSkillsManager as MockMSM, \
    SkillRepo as MockSkillRepo

from ovos_utils.configuration import get_xdg_data_save_path

import warnings

warnings.warn(
    "The OpenVoiceOS team regards msm_wrapper.py as dead code. "
    "It's available for backwards compatibility with upstream projects, and may be removed in a future update. "
    "If you need this functionality use the msm package directly instead"
)


try:
    from msm.exceptions import MsmException
    from msm import MycroftSkillsManager, SkillRepo
except ImportError:
    MycroftSkillsManager = MockMSM
    SkillRepo = MockSkillRepo
    from mock_msm.exceptions import MsmException

MsmConfig = namedtuple(
    'MsmConfig',
    [
        'platform',
        'repo_branch',
        'repo_cache',
        'repo_url',
        'skills_dir',
        'old_skills_dir',
        'versioned',
        'disabled'
    ]
)


def _init_msm_lock():
    msm_lock = None
    try:
        msm_lock = ComboLock(get_temp_path('mycroft-msm.lck'))
        LOG.debug('mycroft-msm combo lock instantiated')
    except Exception:
        LOG.exception('Failed to create msm lock!')

    return msm_lock


def build_msm_config(device_config: dict) -> MsmConfig:
    LOG.warning("build_msm_config has been deprecated\n"
                "use msm package directly instead")
    msm_config = device_config['skills'].get('msm', {})
    msm_repo_config = msm_config.get('repo', {})
    enclosure_config = device_config.get('enclosure', {})
    data_dir = path.expanduser(device_config.get('data_dir', get_xdg_data_save_path()))
    skills_dir = get_default_skills_directory(device_config)
    old_skills_dir = path.join(data_dir, msm_config.get('directory', "skills"))

    return MsmConfig(
        platform=enclosure_config.get('platform', 'default'),
        repo_branch=msm_repo_config.get('branch', "21.02"),
        repo_cache=path.join(data_dir, msm_repo_config.get(
            'cache', ".skills-repo")),
        repo_url=msm_repo_config.get(
            'url', "https://github.com/MycroftAI/mycroft-skills"),
        skills_dir=skills_dir,
        old_skills_dir=old_skills_dir,
        versioned=msm_config.get('versioned', True),
        disabled=msm_config.get("disabled", not msm_config)
    )


def create_msm(msm_config: MsmConfig) -> MycroftSkillsManager:
    """Returns an instantiated MSM object.

    This function is cached because it can take as long as 15 seconds to
    instantiate MSM.  Caching the instance improves performance significantly,
    especially during the boot sequence when this function is called multiple
    times.
    """
    if msm_config.disabled:
        LOG.debug("MSM is disabled, using mock_msm")
        repo_clazz = MockSkillRepo
        msm_clazz = MockMSM
    else:
        repo_clazz = SkillRepo
        msm_clazz = MycroftSkillsManager

    if msm_config.repo_url != "https://github.com/MycroftAI/mycroft-skills":
        LOG.warning("You have enabled a third-party skill store.\n"
                    "Unable to guarantee the safety of skills from "
                    "sources other than the Mycroft Marketplace.\n"
                    "Proceed with caution.")
    msm_lock = _init_msm_lock()
    LOG.debug('Acquiring lock to instantiate MSM')
    with msm_lock:
        if not path.exists(msm_config.skills_dir):
            makedirs(msm_config.skills_dir)

        # NOTE newer versions of msm do not have repo_cache param
        # XDG support is version dependent
        try:
            msm_skill_repo = repo_clazz(
                msm_config.repo_cache,
                msm_config.repo_url,
                msm_config.repo_branch
            )
        except:
            msm_skill_repo = repo_clazz(
                msm_config.repo_url,
                msm_config.repo_branch
            )

        # NOTE older versions of msm do not have old_skills_dir param
        # XDG support is version dependent
        try:
            msm_instance = msm_clazz(
                platform=msm_config.platform,
                old_skills_dir=msm_config.old_skills_dir,
                repo=msm_skill_repo,
                skills_dir=msm_config.skills_dir,
                versioned=msm_config.versioned
            )
        except:
            msm_instance = msm_clazz(
                platform=msm_config.platform,
                skills_dir=msm_config.skills_dir,
                repo=msm_skill_repo,
                versioned=msm_config.versioned
            )
    LOG.debug('Releasing MSM instantiation lock.')

    return msm_instance
