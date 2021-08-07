# Copyright (c) 2018 Mycroft AI, Inc.
#
# This file is part of Mycroft Skills Kit
# (see https://github.com/MycroftAI/mycroft-skills-kit).
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
import sys

from argparse import ArgumentParser
from msm import MycroftSkillsManager, SkillRepo

from msk.actions.create import CreateAction
from msk.actions.create_test import CreateTestAction
from msk.actions.submit import SubmitAction
from msk.exceptions import MskException
from msk.global_context import GlobalContext
from msk.util import ensure_git_user
action_names = {
    SubmitAction: ['submit', 'update', 'upgrade', 'upload'],
    CreateAction: ['create'],
    CreateTestAction: ['create-test']
}


def main():
    parser = ArgumentParser()
    parser.add_argument('-l', '--lang', default='en-us')
    parser.add_argument('-u', '--repo-url', help='Url of GitHub repo to upload skills to')
    parser.add_argument('-b', '--repo-branch', help='Branch of skills repo to upload to')
    parser.add_argument('-s', '--skills-dir', help='Directory to look for skills in')
    parser.add_argument('-c', '--repo-cache', help='Location to store local skills repo clone')

    subparsers = parser.add_subparsers(dest='action')
    subparsers.required = True
    action_to_cls = {}
    for cls, names in action_names.items():
        cls.register(subparsers.add_parser(names[0], aliases=names[1:]))
        action_to_cls.update({name: cls for name in names})

    args = parser.parse_args(sys.argv[1:])

    ensure_git_user()
    context = GlobalContext()
    context.lang = args.lang
    context.msm = MycroftSkillsManager(
        skills_dir=args.skills_dir, repo=SkillRepo(url=args.repo_url, 
                                                   branch=args.repo_branch,
                                                   path=args.repo_cache)
    )
    context.branch = context.msm.repo.branch

    try:
        return action_to_cls[args.action](args).perform()
    except MskException as e:
        print('{}: {}'.format(e.__class__.__name__, str(e)))
    except (KeyboardInterrupt, EOFError):
        pass


if __name__ == '__main__':
    main()
