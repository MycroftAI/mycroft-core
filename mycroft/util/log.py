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


"""
Mycroft Logging module.

This module provides the LOG pseudo function quickly creating a logger instance
for use.

The default log level of the logger created here can ONLY be set in
/etc/mycroft/mycroft.conf or ~/.mycroft/mycroft.conf

The default log level can also be programatically be changed by setting the
LOG.level parameter.
"""

import logging
import sys

from os.path import isfile

from mycroft.util.json_helper import load_commented_json, merge_dict
from mycroft.configuration.locations import SYSTEM_CONFIG, USER_CONFIG


def getLogger(name="MYCROFT"):
    """Depreciated. Use LOG instead"""
    return logging.getLogger(name)


def _make_log_method(fn):
    @classmethod
    def method(cls, *args, **kwargs):
        cls._log(fn, *args, **kwargs)

    method.__func__.__doc__ = fn.__doc__
    return method


LOG = logging.getLogger('Mycroft')


def create_logger(name):
    log_message_format = ('{asctime} | {levelname:8} | {process:5} | '
                          '{name} | {message}')
    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter(log_message_format, style='{')
    formatter.default_msec_format = '%s.%03d'
    handler.setFormatter(formatter)

    logger = LOG.getChild(name)
    logger.addHandler(handler)
    logger.propagate = False
    logger.addHandler(handler)
    return logger


def setup_default_logger(level='INFO'):
    """ Setup the default logger."""
    log_message_format = ('{asctime} | {levelname:8} | {process:5} | '
                          '{module}:{lineno} | {message}')
    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter(log_message_format, style='{')
    formatter.default_msec_format = '%s.%03d'
    handler.setFormatter(formatter)
    LOG.addHandler(handler)

    # Check configs manually, the Mycroft configuration system can't be
    # used since it uses the LOG system and would cause horrible cyclic
    # dependencies.
    confs = [SYSTEM_CONFIG, USER_CONFIG]
    config = {}
    for conf in confs:
        try:
            merge_dict(config,
                       load_commented_json(conf) if isfile(conf) else {})
        except Exception as e:
            print('couldn\'t load {}: {}'.format(conf, str(e)))
    LOG.setLevel(logging.getLevelName(config.get('log_level', level)))

    # Backwards compatibility, TODO: remove in 20.02
    LOG.create_logger = create_logger


setup_default_logger()
