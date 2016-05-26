# Copyright 2016 Mycroft AI, Inc.
#
# This file is part of Mycroft Core.
#
# Mycroft Core is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Mycroft Core is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Mycroft Core.  If not, see <http://www.gnu.org/licenses/>.


import os
import requests
from configobj import ConfigObj
import collections

from mycroft.identity import IdentityManager
from mycroft.util import str2bool
from mycroft.util.log import getLogger

__author__ = 'seanfitz'

logger = getLogger(__name__)
DEFAULTS_FILE = os.path.join(
    os.path.dirname(__file__), 'defaults', 'defaults.ini')
ETC_CONFIG_FILE = '/etc/mycroft/mycroft.ini'
USER_CONFIG_FILE = os.path.join(
    os.path.expanduser('~'), '.mycroft/mycroft.ini')
DEFAULT_LOCATIONS = [DEFAULTS_FILE, ETC_CONFIG_FILE, USER_CONFIG_FILE]


class ConfigurationLoader(object):
    """
    A utility for loading mycroft configuration files.
    """
    def __init__(self, config_locations):
        self.config_locations = config_locations

    @staticmethod
    def _overwrite_merge(d, u):
        for k, v in u.iteritems():
            if isinstance(v, collections.Mapping):
                r = ConfigurationLoader._overwrite_merge(d.get(k, {}), v)
                d[k] = r
            else:
                d[k] = u[k]
        return d

    def load(self):
        """
        Loads configuration files from disk, in the locations defined by
        DEFAULT_LOCATIONS
        """
        config = {}
        for config_file in self.config_locations:
            if os.path.exists(config_file) and os.path.isfile(config_file):
                logger.debug("Loading config file [%s]" % config_file)
                try:
                    cobj = ConfigObj(config_file)
                    config = ConfigurationLoader._overwrite_merge(config, cobj)
                except Exception, e:
                    logger.error(
                        "Error loading config file [%s]" % config_file)
                    logger.error(repr(e))
            else:
                logger.debug(
                    "Could not find config file at [%s]" % config_file)
        return config


class RemoteConfiguration(object):
    """
    map remote configuration properties to
    config in the [core] config section
    """
    remote_config_mapping = {
        "default_location": "location",
        "default_language": "lang",
        "timezone": "timezone"
    }

    def __init__(self, identity=None):
        self.identity = identity or IdentityManager().get()
        self.config_manager = ConfigurationManager()

    def update(self):
        config = self.config_manager.get_config()
        remote_config_url = config.get("remote_configuration").get("url")
        enabled = str2bool(
            config.get("remote_configuration").get("enabled", "False"))
        if enabled and self.identity.token:
            auth_header = "Bearer %s:%s" % (
                self.identity.device_id, self.identity.token)
            try:
                response = requests.get(
                    remote_config_url, headers={"Authorization": auth_header})
                user = response.json()
                for attribute in user["attributes"]:
                    attribute_name = attribute.get("attribute_name")
                    core_config_name = self.remote_config_mapping.get(
                        attribute_name)
                    if core_config_name:
                        config["core"][core_config_name] = str(
                            attribute.get("attribute_value"))
                        logger.info(
                            "Accepting remote configuration: core[%s] == %s" %
                            (core_config_name, attribute["attribute_value"]))
            except Exception as e:
                logger.error(
                    "Failed to fetch remote configuration: %s" % repr(e))

        else:
            logger.debug(
                "Device not paired, cannot retrieve remote configuration.")


class ConfigurationManager(object):
    """
    Static management utility for calling up cached configuration.
    """
    _config = None

    @staticmethod
    def load(*config_files):
        """
        Load default config files as well as any additionally specified files.
        Now also loads configuration from Cerberus (if device is paired)

        :param config_files: An array of config file paths in addition to
        DEFAULT_LOCATIONS

        :return: None
        """
        loader = ConfigurationLoader(DEFAULT_LOCATIONS + list(config_files))
        ConfigurationManager._config = loader.load()
        RemoteConfiguration().update()

    @staticmethod
    def get_config():
        """
        Get or create and get statically cached configuration.

        :return: A dictionary representing config files.
        """
        if not ConfigurationManager._config:
            ConfigurationManager.load()
        return ConfigurationManager._config
