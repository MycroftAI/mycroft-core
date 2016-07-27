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
import collections

import requests
from configobj import ConfigObj
from genericpath import exists, isfile
from os.path import join, dirname, expanduser

from mycroft.identity import IdentityManager
from mycroft.util import str2bool
from mycroft.util.log import getLogger

__author__ = 'seanfitz, jdorleans'

logger = getLogger(__name__)

DEFAULT_CONFIG = join(dirname(__file__), 'mycroft.ini')
SYSTEM_CONFIG = '/etc/mycroft/mycroft.ini'
USER_CONFIG = join(expanduser('~'), '.mycroft/mycroft.ini')


class ConfigurationLoader(object):
    """
    A utility for loading Mycroft configuration files.
    """

    @staticmethod
    def init_config(config=None):
        if not config:
            return {}
        return config

    @staticmethod
    def init_locations(locations=None, keep_user_config=True):
        if not locations:
            locations = [DEFAULT_CONFIG, SYSTEM_CONFIG, USER_CONFIG]
        elif keep_user_config:
            locations += [USER_CONFIG]
        return locations

    @staticmethod
    def validate_data(config=None, locations=None):
        if not (isinstance(config, dict) and isinstance(locations, list)):
            logger.error("Invalid configuration data type.")
            logger.error("Locations: %s" % locations)
            logger.error("Configuration: %s" % config)
            raise TypeError

    @staticmethod
    def load(config=None, locations=None, keep_user_config=True):
        """
        Loads default or specified configuration files
        """
        config = ConfigurationLoader.init_config(config)
        locations = ConfigurationLoader.init_locations(locations,
                                                       keep_user_config)
        ConfigurationLoader.validate_data(config, locations)

        for location in locations:
            config = ConfigurationLoader.__load(config, location)

        return config

    @staticmethod
    def __load(config, location):
        if exists(location) and isfile(location):
            try:
                cobj = ConfigObj(location)
                config = ConfigurationLoader.__merge(config, cobj)
                logger.debug("Configuration '%s' loaded" % location)
            except Exception, e:
                logger.error("Error loading configuration '%s'" % location)
                logger.error(repr(e))
        else:
            logger.debug("Configuration '%s' not found" % location)
        return config

    @staticmethod
    def __merge(config, cobj):
        for k, v in cobj.iteritems():
            if isinstance(v, collections.Mapping):
                config[k] = ConfigurationLoader.__merge(config.get(k, {}), v)
            else:
                config[k] = cobj[k]
        return config


class RemoteConfiguration(object):
    """
    map remote configuration properties to
    config in the [core] config section
    """
    __remote_keys = {
        "default_location": "location",
        "default_language": "lang",
        "timezone": "timezone"
    }

    @staticmethod
    def validate_config(config):
        if not (config and isinstance(config, dict)):
            logger.error("Invalid configuration: %s" % config)
            raise TypeError

    @staticmethod
    def load(config=None):
        RemoteConfiguration.validate_config(config)

        identity = IdentityManager().get()
        config_remote = config.get("remote_configuration", {})
        enabled = str2bool(config_remote.get("enabled", "False"))

        if enabled and identity.token:
            url = config_remote.get("url")
            auth_header = "Bearer %s:%s" % (identity.device_id, identity.token)
            try:
                response = requests.get(url,
                                        headers={"Authorization": auth_header})
                user = response.json()
                RemoteConfiguration.__load_attributes(config, user)
            except Exception as e:
                logger.error(
                    "Failed to fetch remote configuration: %s" % repr(e))
        else:
            logger.debug(
                "Device not paired, cannot retrieve remote configuration.")
        return config

    @staticmethod
    def __load_attributes(config, user):
        config_core = config["core"]

        for att in user["attributes"]:
            att_name = att.get("attribute_name")
            name = RemoteConfiguration.__remote_keys.get(att_name)

            if name:
                config_core[name] = str(att.get("attribute_value"))
                logger.info(
                    "Accepting remote configuration: core[%s] == %s" %
                    (name, att["attribute_value"]))


class ConfigurationManager(object):
    """
    Static management utility for calling up cached configuration.
    """
    __config = None

    @staticmethod
    def load_defaults():
        ConfigurationManager.__config = ConfigurationLoader.load()
        return RemoteConfiguration.load(ConfigurationManager.__config)

    @staticmethod
    def load_local(locations=None, keep_user_config=True):
        return ConfigurationLoader.load(ConfigurationManager.get(), locations,
                                        keep_user_config)

    @staticmethod
    def load_remote():
        if not ConfigurationManager.__config:
            ConfigurationManager.__config = ConfigurationLoader.load()
        return RemoteConfiguration.load(ConfigurationManager.__config)

    @staticmethod
    def get(locations=None):
        """
        Get cached configuration.

        :return: A dictionary representing Mycroft configuration.
        """
        if not ConfigurationManager.__config:
            ConfigurationManager.load_defaults()

        if locations:
            ConfigurationManager.load_local(locations)

        return ConfigurationManager.__config

    @staticmethod
    def set(section, key, value):
        """
        Set a key in the user preferences
        """
        if not ConfigurationManager.__config:
            ConfigurationManager.load_defaults()

        ConfigurationManager.__config[section][key] = value

        user_config = ConfigObj(USER_CONFIG)
        user_config.setdefault(section, {})
        user_config[section][key] = value
        user_config.write()
