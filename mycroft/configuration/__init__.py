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
import json

import inflection
import re
from genericpath import exists, isfile
from os.path import join, dirname, expanduser

from mycroft.util.json_helper import load_commented_json
from mycroft.util.log import LOG


DEFAULT_CONFIG = join(dirname(__file__), 'mycroft.conf')
SYSTEM_CONFIG = '/etc/mycroft/mycroft.conf'
USER_CONFIG = join(expanduser('~'), '.mycroft/mycroft.conf')
REMOTE_CONFIG = "mycroft.ai"

load_order = [DEFAULT_CONFIG, REMOTE_CONFIG, SYSTEM_CONFIG, USER_CONFIG]


class ConfigurationLoader(object):
    """
    A utility for loading Mycroft configuration files.

    Mycroft configuration comes from four potential locations:
     * Defaults found in 'mycroft.conf' in the code
     * Remote settings (coming from home.mycroft.ai)
     * System settings (typically found at /etc/mycroft/mycroft.conf
     * User settings (typically found at /home/<user>/.mycroft/mycroft.conf
    These get loaded in that order on top of each other.  So a value specified
    in the Default would be overridden by a value with the same name found
    in the Remote.  And a value in the Remote would be overridden by a value
    set in the User settings.  Not all values exist at all levels.

    See comments in the 'mycroft.conf' for more information about specific
    settings and where they reside.

    Note:
        Values are overridden by name.  This includes all data under that name,
        so you if a value contains a complex structure, you cannot specify
        only a single component of that structure -- you have to override the
        entire structure.
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
    def merge_conf(base, delta):
        """
            Recursively merging configuration dictionaries.

            Args:
                base:  Target for merge
                delta: Dictionary to merge into base
        """

        for k, dv in delta.iteritems():
            bv = base.get(k)
            if isinstance(dv, dict) and isinstance(bv, dict):
                ConfigurationLoader.merge_conf(bv, dv)
            else:
                base[k] = dv

    @staticmethod
    def __load(config, location):
        if exists(location) and isfile(location):
            try:
                ConfigurationLoader.merge_conf(
                    config, load_commented_json(location))
                LOG.debug("Configuration '%s' loaded" % location)
            except Exception, e:
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
    WEB_CONFIG_CACHE = '/opt/mycroft/web_config_cache.json'

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
                RemoteConfiguration.__store_cache(setting)
            except Exception as e:
                LOG.warning("Failed to fetch remote configuration: %s" %
                            repr(e))
                RemoteConfiguration.__load_cache(config)

        else:
            LOG.debug("Remote configuration not activated.")
        return config

    @staticmethod
    def __load(config, setting):
        for k, v in setting.iteritems():
            if k not in RemoteConfiguration.IGNORED_SETTINGS:
                # Translate the CamelCase values stored remotely into the
                # Python-style names used within mycroft-core.
                key = inflection.underscore(re.sub(r"Setting(s)?", "", k))
                if isinstance(v, dict):
                    config[key] = config.get(key, {})
                    RemoteConfiguration.__load(config[key], v)
                elif isinstance(v, list):
                    if key not in config:
                        config[key] = {}
                    RemoteConfiguration.__load_list(config[key], v)
                else:
                    config[key] = v

    @staticmethod
    def __store_cache(setting):
        """
            Cache the received settings locally. The cache will be used if
            the remote is unreachable to load settings that are as close
            to the user's as possible
        """
        config = {}
        # Remove server specific entries
        RemoteConfiguration.__load(config, setting)
        with open(RemoteConfiguration.WEB_CONFIG_CACHE, 'w') as f:
            json.dump(config, f)

    @staticmethod
    def __load_cache(config):
        """
            Load cache from file
        """
        LOG.info("Using cached configuration if available")
        ConfigurationLoader.load(config,
                                 [RemoteConfiguration.WEB_CONFIG_CACHE],
                                 False)

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
    Static management utility for accessing the cached configuration.
    This configuration is periodically updated from the remote server
    to keep in sync.
    """

    __config = None
    __listener = None

    @staticmethod
    def instance():
        """
        The cached configuration.

        Returns:
            dict: A dictionary representing the Mycroft configuration
        """
        return ConfigurationManager.get()

    @staticmethod
    def init(ws):
        # Start listening for configuration update events on the messagebus
        ConfigurationManager.__listener = _ConfigurationListener(ws)

    @staticmethod
    def load_defaults():
        for location in load_order:
            LOG.info("Loading configuration: " + location)
            if location == REMOTE_CONFIG:
                RemoteConfiguration.load(ConfigurationManager.__config)
            else:
                ConfigurationManager.__config = ConfigurationLoader.load(
                    ConfigurationManager.__config, [location])
        return ConfigurationManager.__config

    @staticmethod
    def load_local(locations=None, keep_user_config=True):
        return ConfigurationLoader.load(ConfigurationManager.get(), locations,
                                        keep_user_config)

    @staticmethod
    def load_internal(config):
        LOG.info("Updating config internally")
        ConfigurationManager.update(config)

    @staticmethod
    def load_remote():
        if not ConfigurationManager.__config:
            ConfigurationManager.__config = ConfigurationLoader.load()
        return RemoteConfiguration.load(ConfigurationManager.__config)

    @staticmethod
    def get(locations=None):
        """
        Get cached configuration.

        Returns:
            dict: A dictionary representing the Mycroft configuration
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
        try:
            LOG.info("Saving config")
            loc_config = load_commented_json(location)
            with open(location, 'w') as f:
                ConfigurationLoader.merge_conf(loc_config, config)
                json.dump(loc_config, f)
        except Exception as e:
            LOG.error(e)


class _ConfigurationListener(object):
    """ Utility to synchronize remote configuration changes locally

    This listens to the messagebus for
    'configuration.updated', and refreshes the cached configuration when this
    is encountered.
     'configuration.update', and updates the cached configuration when this
    is encountered.

    """

    def __init__(self, ws):
        super(_ConfigurationListener, self).__init__()
        ws.on("configuration.updated", self.updated)
        ws.on("configuration.patch", self.patch)

    @staticmethod
    def updated(message):
        """
            Event handler for configuration updated events. Forces a reload
            of all configuration sources.

            Args:
                message:    message bus message structure
        """
        ConfigurationManager.load_defaults()

    @staticmethod
    def patch(message):
        """
            Event handler for configuration update events.
            Update config with provided data
            Args:
                message:    message bus message structure
        """
        config = message.data.get("config", {})
        ConfigurationManager.load_internal(config)
