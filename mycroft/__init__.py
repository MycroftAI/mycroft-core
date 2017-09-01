from mycroft.api import Api
from mycroft.skills.core import MycroftSkill, FallbackSkill, \
    intent_handler, intent_file_handler
from mycroft.skills.context import adds_context, removes_context
from mycroft.messagebus.message import Message

from os.path import abspath, dirname, join

__author__ = 'seanfitz'

MYCROFT_ROOT_PATH = abspath(join(dirname(__file__), '..'))
