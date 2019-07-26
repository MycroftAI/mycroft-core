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
#
""" Collection of core functions of the mycroft skills system.

This file is now depricated and skill should now import directly from
mycroft.skills.
"""
import imp
from os.path import basename, join
from mycroft.util.log import LOG

# Import moved methods for backwards compatibility
# This will need to remain here for quite some time since removing it
# would break most of the skills out there.
import mycroft.skills.mycroft_skill as mycroft_skill
import mycroft.skills.fallback_skill as fallback_skill
from .mycroft_skill import *  # noqa


class MycroftSkill(mycroft_skill.MycroftSkill):
    # Compatibility, needs to be kept for a while to not break every skill
    pass


class FallbackSkill(fallback_skill.FallbackSkill):
    # Compatibility, needs to be kept for a while to not break every skill
    pass


MainModule = '__init__'


def load_skill(skill_descriptor, bus, skill_id, BLACKLISTED_SKILLS=None):
    """ Load skill from skill descriptor.

    Args:
        skill_descriptor: descriptor of skill to load
        bus:              Mycroft messagebus connection
        skill_id:         id number for skill
        use_settings:     (default True) selects if the skill should create
                          a settings object.

    Returns:
        MycroftSkill: the loaded skill or None on failure
    """
    BLACKLISTED_SKILLS = BLACKLISTED_SKILLS or []
    path = skill_descriptor["path"]
    name = basename(path)
    LOG.info("ATTEMPTING TO LOAD SKILL: {} with ID {}".format(name, skill_id))
    if name in BLACKLISTED_SKILLS:
        LOG.info("SKILL IS BLACKLISTED " + name)
        return None
    main_file = join(path, MainModule + '.py')
    try:
        with open(main_file, 'rb') as fp:
            skill_module = imp.load_module(name.replace('.', '_'), fp,
                                           main_file, ('.py', 'rb',
                                           imp.PY_SOURCE))
        if (hasattr(skill_module, 'create_skill') and
                callable(skill_module.create_skill)):
            # v2 skills framework
            skill = skill_module.create_skill()
            skill.skill_id = skill_id
            skill.settings.allow_overwrite = True
            skill.settings.load_skill_settings_from_file()
            skill.bind(bus)
            try:
                skill.load_data_files(path)
                # Set up intent handlers
                skill._register_decorated()
                skill.register_resting_screen()
                skill.initialize()
            except Exception as e:
                # If an exception occurs, make sure to clean up the skill
                skill.default_shutdown()
                raise e

            LOG.info("Loaded " + name)
            # The very first time a skill is run, speak the intro
            first_run = skill.settings.get("__mycroft_skill_firstrun", True)
            if first_run:
                LOG.info("First run of " + name)
                skill.settings["__mycroft_skill_firstrun"] = False
                skill.settings.store()
                intro = skill.get_intro_message()
                if intro:
                    skill.speak(intro)
            return skill
        else:
            LOG.warning("Module {} does not appear to be skill".format(name))
    except FileNotFoundError as e:
        LOG.error(
            'Failed to load {} due to a missing file: {}'.format(name, str(e))
            )
    except Exception:
        LOG.exception("Failed to load skill: " + name)
    return None


def create_skill_descriptor(skill_path):
    return {"path": skill_path}
