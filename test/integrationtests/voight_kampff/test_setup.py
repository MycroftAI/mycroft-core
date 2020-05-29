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
from argparse import RawTextHelpFormatter
from glob import glob
from os.path import join, dirname, expanduser, basename, exists
from random import shuffle
import shutil
import sys

import yaml
from msm import MycroftSkillsManager, SkillRepo
from msm.exceptions import MsmException

from .generate_feature import generate_feature

"""Test environment setup for voigt kampff test

The script sets up the selected tests in the feature directory so they can
be found and executed by the behave framework.

The script also ensures that the skills marked for testing are installed and
that any specified extra skills also gets installed into the environment.
"""

FEATURE_DIR = join(dirname(__file__), 'features') + '/'


def copy_config_definition_files(source, destination):
    """Copy all feature files from source to destination."""
    # Copy feature files to the feature directory
    for f in glob(join(source, '*.config.json')):
        shutil.copyfile(f, join(destination, basename(f)))


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


def apply_config(config, args):
    """Load config and add to unset arguments."""
    with open(expanduser(config)) as f:
        conf_dict = yaml.safe_load(f)

    if not args.test_skills and 'test_skills' in conf_dict:
        args.test_skills = conf_dict['test_skills']
    if not args.extra_skills and 'extra_skills' in conf_dict:
        args.extra_skills = conf_dict['extra_skills']
    if not args.platform and 'platform' in conf_dict:
        args.platform = conf_dict['platform']


def create_argument_parser():
    """Create the argument parser for the command line options.

    Returns: ArgumentParser
    """
    class TestSkillAction(argparse.Action):
        def __call__(self, parser, args, values, option_string=None):
            args.test_skills = values.replace(',', ' ').split()

    class ExtraSkillAction(argparse.Action):
        def __call__(self, parser, args, values, option_string=None):
            args.extra_skills = values.replace(',', ' ').split()

    platforms = list(MycroftSkillsManager.SKILL_GROUPS)
    parser = argparse.ArgumentParser(formatter_class=RawTextHelpFormatter)
    parser.add_argument('-p', '--platform', choices=platforms,
                        default='mycroft_mark_1')
    parser.add_argument('-t', '--test-skills', default=[],
                        action=TestSkillAction,
                        help=('Comma-separated list of skills to test.\n'
                              'Ex: "mycroft-weather, mycroft-stock"'))
    parser.add_argument('-s', '--extra-skills', default=[],
                        action=ExtraSkillAction,
                        help=('Comma-separated list of extra skills to '
                              'install.\n'
                              'Ex: "cocktails, laugh"'))
    parser.add_argument('-r', '--random-skills', default=0, type=int,
                        help='Number of random skills to install.')
    parser.add_argument('-d', '--skills-dir')
    parser.add_argument('-u', '--repo-url',
                        help='URL for skills repo to install / update from')
    parser.add_argument('-b', '--branch',
                        help='repo branch to use')
    parser.add_argument('-c', '--config',
                        help='Path to test configuration file.')
    return parser


def get_random_skills(msm, num_random_skills):
    """Install random skills from uninstalled skill list."""
    random_skills = [s for s in msm.all_skills if not s.is_local]
    shuffle(random_skills)  # Make them random
    return [s.name for s in random_skills[:num_random_skills]]


def install_or_upgrade_skills(msm, skills):
    """Install needed skills if uninstalled, otherwise try to update.

    Arguments:
        msm: msm instance to use for the operations
        skills: list of skills
    """
    skills = [msm.find_skill(s) for s in skills]
    for s in skills:
        if not s.is_local:
            print('Installing {}'.format(s))
            msm.install(s)
        else:
            try:
                msm.update(s)
            except MsmException:
                pass


def collect_test_cases(msm, skills):
    """Collect feature files and step files for each skill.

    Arguments:
        msm: msm instance to use for the operations
        skills: list of skills
    """
    for skill_name in skills:
        skill = msm.find_skill(skill_name)
        behave_dir = join(skill.path, 'test', 'behave')
        if exists(behave_dir):
            copy_feature_files(behave_dir, FEATURE_DIR)
            copy_config_definition_files(behave_dir, FEATURE_DIR)

            step_dir = join(behave_dir, 'steps')
            if exists(step_dir):
                copy_step_files(step_dir, join(FEATURE_DIR, 'steps'))
        else:
            # Generate feature file if no data exists yet
            print('No feature files exists for {}, '
                  'generating...'.format(skill_name))
            # No feature files setup, generate automatically
            feature = generate_feature(skill_name, skill.path)
            with open(join(FEATURE_DIR, skill_name + '.feature'), 'w') as f:
                f.write(feature)


def print_install_report(platform, test_skills, extra_skills):
    """Print in nice format."""
    print('-------- TEST SETUP --------')
    yml = yaml.dump({
        'platform': platform,
        'test_skills': test_skills,
        'extra_skills': extra_skills
        })
    print(yml)
    print('----------------------------')


def get_arguments(cmdline_args):
    """Get arguments for test setup.

    Parses the commandline and if specified applies configuration file.

    Arguments:
        cmdline_args (list): argv like list of arguments

    Returns:
        Argument parser NameSpace
    """
    parser = create_argument_parser()
    args = parser.parse_args(cmdline_args)
    return args


def create_skills_manager(platform, skills_dir, url, branch):
    """Create mycroft skills manager for the given url / branch.

    Arguments:
        platform (str): platform to use
        skills_dir (str): skill directory to use
        url (str): skills repo url
        branch (str): skills repo branch

    Returns:
        MycroftSkillsManager
    """
    repo = SkillRepo(url=url, branch=branch)
    return MycroftSkillsManager(platform, skills_dir, repo)


def main(args):
    """Parse arguments and run test environment setup.

    This installs and/or upgrades any skills needed for the tests and
    collects the feature and step files for the skills.
    """
    if args.config:
        apply_config(args.config, args)

    msm = create_skills_manager(args.platform, args.skills_dir,
                                args.repo_url, args.branch)

    random_skills = get_random_skills(msm, args.random_skills)
    all_skills = args.test_skills + args.extra_skills + random_skills

    install_or_upgrade_skills(msm, all_skills)
    collect_test_cases(msm, args.test_skills)

    print_install_report(msm.platform, args.test_skills,
                         args.extra_skills + random_skills)


if __name__ == '__main__':
    main(get_arguments(sys.argv[1:]))
