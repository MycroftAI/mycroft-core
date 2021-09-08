"""
mode of operation is defined in the .conf file for the different components
"""
import enum


class ConverseMode(str, enum.Enum):
    ACCEPT_ALL = "accept_all"  # default mycroft-core behavior
    WHITELIST = "whitelist"  # only call converse for skills in whitelist
    BLACKLIST = "blacklist"  # only call converse for skills NOT in blacklist


class FallbackMode(str, enum.Enum):
    ACCEPT_ALL = "accept_all"  # default mycroft-core behavior
    WHITELIST = "whitelist"  # only call fallback for skills in whitelist
    BLACKLIST = "blacklist"  # only call fallback for skills NOT in blacklist


class ConverseActivationMode(str, enum.Enum):
    ACCEPT_ALL = "accept_all"  # default mycroft-core behavior
    PRIORITY = "priority"  # skills can only activate themselves if no skill
                           # with higher priority is active
    WHITELIST = "whitelist"  # only skills in "converse_whitelist"
                             # can activate themselves
    BLACKLIST = "blacklist"  # only skills NOT in converse "converse_blacklist"
                             # can activate themselves
