from os.path import abspath, dirname, join

from mycroft.api import Api
from mycroft.messagebus.message import Message
from mycroft.skills.context import adds_context, removes_context
from mycroft.skills.core import MycroftSkill, FallbackSkill, \
    intent_handler, intent_file_handler

__author__ = 'seanfitz'

MYCROFT_ROOT_PATH = abspath(join(dirname(__file__), '..'))
