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
from os.path import abspath, dirname, join
import mycroft.configuration
from mycroft.api import Api
from mycroft.messagebus.message import Message

# don't require adapt to be installed to import non-skill stuff
try:
    from mycroft.skills.context import adds_context, removes_context
    from mycroft.skills import (MycroftSkill, FallbackSkill,
                                intent_handler, intent_file_handler)
    from mycroft.skills.intent_service import AdaptIntent
except ImportError:
    # skills requirements not installed
    # i would remove this completely, but some skills in the wild import
    # from the top level module instead of mycroft.skills
    pass
from mycroft.util.log import LOG

MYCROFT_ROOT_PATH = abspath(join(dirname(__file__), '..'))

__all__ = ['MYCROFT_ROOT_PATH',
           'Api',
           'Message']

LOG.init()  # read log level from config
