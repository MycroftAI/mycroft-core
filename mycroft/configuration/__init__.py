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
import json
import re
from genericpath import exists, isfile
from os.path import join, dirname, expanduser

import inflection

from mycroft.util.log import getLogger

__author__ = 'seanfitz, jdorleans'

LOG = getLogger(__name__)

DEFAULT_CONFIG = join(dirname(__file__), 'mycroft.conf')
SYSTEM_CONFIG = '/etc/mycroft/mycroft.conf'
USER_CONFIG = join(expanduser('~'), '.mycroft/mycroft.conf')


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
    def validate(config=None, locations=None):
        if not (isinstance(config, dict) and isinstance(locations, list)):
            LOG.error("Invalid configuration data type.")
            LOG.error("Locations: %s" % locations)
            LOG.error("Configuration: %s" % config)
            raise TypeError

    @staticmethod
    def load(config=None, locations=None, keep_user_config=True):
        """
        Loads default or specified configuration files
        """
        config = ConfigurationLoader.init_config(config)
        locations = ConfigurationLoader.init_locations(locations,
                                                       keep_user_config)
        ConfigurationLoader.validate(config, locations)

        for location in locations:
            config = ConfigurationLoader.__load(config, location)

        return config

    @staticmethod
    def __load(config, location):
        if exists(location) and isfile(location):
            try:
                with open(location) as f:
                    config.update(json.load(f))
                    LOG.debug("Configuration '%s' loaded" % location)
            except Exception as e:
                LOG.error("Error loading configuration '%s'" % location)
                LOG.error(repr(e))
        else:
            LOG.debug("Configuration '%s' not found" % location)
        return config


class RemoteConfiguration(object):
    """
    map remote configuration properties to
    config in the [core] config section
    """
    IGNORED_SETTINGS = ["uuid", "@type", "active", "user", "device"]

    @staticmethod
    def validate(config):
        if not (config and isinstance(config, dict)):
            LOG.error("Invalid configuration: %s" % config)
            raise TypeError

    @staticmethod
    def load(config=None):
        RemoteConfiguration.validate(config)
        update = config.get("server", {}).get("update")

        if update:
            try:
                from mycroft.api import DeviceApi
                api = DeviceApi()
                setting = api.find_setting()
                location = api.find_location()
                if location:
                    setting["location"] = location
                RemoteConfiguration.__load(config, setting)
            except Exception as e:
                LOG.warn("Failed to fetch remote configuration: %s" % repr(e))
        else:
            LOG.debug("Remote configuration not activated.")
        return config

    @staticmethod
    def __load(config, setting):
        for k, v in setting.iteritems():
            if k not in RemoteConfiguration.IGNORED_SETTINGS:
                key = inflection.underscore(re.sub(r"Setting(s)?", "", k))
                if isinstance(v, dict):
                    config[key] = config.get(key, {})
                    RemoteConfiguration.__load(config[key], v)
                elif isinstance(v, list):
                    RemoteConfiguration.__load_list(config[key], v)
                else:
                    config[key] = v

    @staticmethod
    def __load_list(config, values):
        for v in values:
            module = v["@type"]
            if v.get("active"):
                config["module"] = module
            config[module] = config.get(module, {})
            RemoteConfiguration.__load(config[module], v)


class ConfigurationManager(object):
    """
    Static management utility for calling up cached configuration.
    """
    __config = None
    __listener = None

    @staticmethod
    def init(ws):
        ConfigurationManager.__listener = ConfigurationListener(ws)

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
    def update(config):
        """
        Update cached configuration with the new ``config``.
        """
        if not ConfigurationManager.__config:
            ConfigurationManager.load_defaults()

        if config:
            ConfigurationManager.__config.update(config)

    @staticmethod
    def save(config, is_system=False):
        """
        Save configuration ``config``.
        """
        ConfigurationManager.update(config)
        location = SYSTEM_CONFIG if is_system else USER_CONFIG
        with open(location, 'rw') as f:
            config = json.load(f).update(config)
            json.dump(config, f)


class ConfigurationListener(object):
    def __init__(self, ws):
        super(ConfigurationListener, self).__init__()
        ws.on("configuration.updated", self.updated)

    @staticmethod
    def updated(message):
        ConfigurationManager.update(message.data)
