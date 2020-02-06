# Copyright 2020 Mycroft AI Inc.
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
import argparse
from glob import glob
from os.path import join, dirname, expanduser, basename
from pathlib import Path
from random import shuffle
import shutil
import sys

import yaml

from msm import MycroftSkillsManager

from .generate_feature import generate_feature

"""Test environment setup for voigt kampff test

The script sets up the selected tests in the feature directory so they can
be found and executed by the behave framework.

The script also ensures that the tested skills are installed and that any
specified extra skills also gets installed into the environment.
"""

FEATURE_DIR = join(dirname(__file__), 'features') + '/'


def copy_feature_files(source, destination):
    """Copy all feature files from source to destination."""
    # Copy feature files to the feature directory
    for f in glob(join(source, '*.feature')):
        shutil.copyfile(f, join(destination, basename(f)))


def copy_step_files(source, destination):
    """Copy all python files from source to destination."""
    # Copy feature files to the feature directory
    for f in glob(join(source, '*.py')):
        shutil.copyfile(f, join(destination, basename(f)))


def load_config(config, args):
    """Load config and add to unset arguments."""
    with open(expanduser(config)) as f:
        conf_dict = yaml.safe_load(f)

    if not args.tested_skills:
        args.tested_skills = conf_dict['tested_skills']
    if not args.extra_skills:
        args.extra_skills = conf_dict['extra_skills']
    if not args.platform:
        args.platform = conf_dict['platform']
    return


def main(cmdline_args):
    """Parse arguments and run environment setup."""
    platforms = list(MycroftSkillsManager.SKILL_GROUPS)
    parser = argparse.ArgumentParser()
    parser.add_argument('-p', '--platform', choices=platforms)
    parser.add_argument('-t', '--tested-skills', default=[])
    parser.add_argument('-s', '--extra-skills', default=[])
    parser.add_argument('-r', '--random-skills', default=0)
    parser.add_argument('-d', '--skills-dir')
    parser.add_argument('-c', '--config')

    args = parser.parse_args(cmdline_args)
    if args.tested_skills:
        args.tested_skills = args.tested_skills.replace(',', ' ').split()
    if args.extra_skills:
        args.extra_skills = args.extra_skills.replace(',', ' ').split()

    if args.config:
        load_config(args.config, args)

    if args.platform is None:
        args.platform = "mycroft_mark_1"

    msm = MycroftSkillsManager(args.platform, args.skills_dir)
    run_setup(msm, args.tested_skills, args.extra_skills, args.random_skills)


def run_setup(msm, test_skills, extra_skills, num_random_skills):
    """Install needed skills and collect feature files for the test."""
    skills = [msm.find_skill(s) for s in test_skills + extra_skills]
    # Install test skills
    for s in skills:
        if not s.is_local:
            print('Installing {}'.format(s))
            msm.install(s)

    # collect feature files
    for skill_name in test_skills:
        skill = msm.find_skill(skill_name)
        behave_dir = join(skill.path, 'test', 'behave')
        if Path(behave_dir).exists():
            copy_feature_files(behave_dir, FEATURE_DIR)

            step_dir = join(behave_dir, 'steps')
            if Path().exists():
                copy_step_files(step_dir, join(FEATURE_DIR, 'steps'))
        else:
            # Generate feature file if no data exists yet
            print('No feature files exists for {}, '
                  'generating...'.format(skill_name))
            # No feature files setup, generate automatically
            feature = generate_feature(skill_name, skill.path)
            with open(join(FEATURE_DIR, skill_name + '.feature'), 'w') as f:
                f.write(feature)

    # Install random skills from uninstalled skill list
    random_skills = [s for s in msm.all_skills if s not in msm.local_skills]
    shuffle(random_skills)  # Make them random
    random_skills = random_skills[:num_random_skills]
    for s in random_skills:
        msm.install(s)

    print_install_report(msm.platform, test_skills,
                         extra_skills + [s.name for s in random_skills])
    return


def print_install_report(platform, test_skills, extra_skills):
    """Print in nice format."""
    print('-------- TEST SETUP --------')
    yml = yaml.dump({
        'platform': platform,
        'tested_skills': test_skills,
        'extra_skills': extra_skills
        })
    print(yml)
    print('----------------------------')


if __name__ == '__main__':
    main(sys.argv[1:])
