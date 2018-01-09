
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

import re
import json
import inflection
from os.path import exists, isfile, join, dirname, expanduser
from requests import HTTPError

from mycroft.util.json_helper import load_commented_json
from mycroft.util.log import LOG

# Python 2+3 compatibility
from future.utils import iteritems
from past.builtins import basestring


def merge_dict(base, delta):
    """
        Recursively merging configuration dictionaries.

        Args:
            base:  Target for merge
            delta: Dictionary to merge into base
    """

    for k, dv in iteritems(delta):
        bv = base.get(k)
        if isinstance(dv, dict) and isinstance(bv, dict):
            merge_dict(bv, dv)
        else:
            base[k] = dv


def translate_remote(config, setting):
    """
        Translate config names from server to equivalents usable
        in mycroft-core.

        Args:
                config:     base config to populate
                settings:   remote settings to be translated
    """
    IGNORED_SETTINGS = ["uuid", "@type", "active", "user", "device"]

    for k, v in iteritems(setting):
        if k not in IGNORED_SETTINGS:
            # Translate the CamelCase values stored remotely into the
            # Python-style names used within mycroft-core.
            key = inflection.underscore(re.sub(r"Setting(s)?", "", k))
            if isinstance(v, dict):
                config[key] = config.get(key, {})
                translate_remote(config[key], v)
            elif isinstance(v, list):
                if key not in config:
                    config[key] = {}
                translate_list(config[key], v)
            else:
                config[key] = v


def translate_list(config, values):
    """
        Translate list formated by mycroft server.

        Args:
            config (dict): target config
            values (list): list from mycroft server config
    """
    for v in values:
        module = v["@type"]
        if v.get("active"):
            config["module"] = module
        config[module] = config.get(module, {})
        translate_remote(config[module], v)


class LocalConf(dict):
    """
        Config dict from file.
    """
    def __init__(self, path):
        super(LocalConf, self).__init__()
        if path:
            self.path = path
            self.load_local(path)

    def load_local(self, path):
        """
            Load local json file into self.

            Args:
                path (str): file to load
        """
        if exists(path) and isfile(path):
            try:
                config = load_commented_json(path)
                for key in config:
                    self.__setitem__(key, config[key])

                LOG.debug("Configuration {} loaded".format(path))
            except Exception as e:
                LOG.error("Error loading configuration '{}'".format(path))
                LOG.error(repr(e))
        else:
            LOG.debug("Configuration '{}' not found".format(path))

    def store(self, path=None):
        """
            Cache the received settings locally. The cache will be used if
            the remote is unreachable to load settings that are as close
            to the user's as possible
        """
        path = path or self.path
        with open(path, 'w') as f:
            json.dump(self, f)

    def merge(self, conf):
        merge_dict(self, conf)


class RemoteConf(LocalConf):
    """
        Config dict fetched from mycroft.ai
    """
    def __init__(self, cache=None):
        super(RemoteConf, self).__init__(None)

        cache = cache or '/opt/mycroft/web_config_cache.json'

        try:
            # Here to avoid cyclic import
            from mycroft.api import DeviceApi
            api = DeviceApi()
            setting = api.get_settings()
            location = api.get_location()
            if location:
                setting["location"] = location
            # Remove server specific entries
            config = {}
            translate_remote(config, setting)
            for key in config:
                self.__setitem__(key, config[key])
            self.store(cache)

        except HTTPError as e:
            LOG.error("HTTPError fetching remote configuration: %s" %
                      e.response.status_code)
            self.load_local(cache)

        except Exception as e:
            LOG.error("Failed to fetch remote configuration: %s" % repr(e),
                      exc_info=True)
            self.load_local(cache)


DEFAULT_CONFIG = join(dirname(__file__), 'mycroft.conf')
SYSTEM_CONFIG = '/etc/mycroft/mycroft.conf'
USER_CONFIG = join(expanduser('~'), '.mycroft/mycroft.conf')
REMOTE_CONFIG = "mycroft.ai"


class Configuration(object):
    __config = {}  # Cached config
    __patch = {}  # Patch config that skills can update to override config

    @staticmethod
    def get(configs=None, cache=True):
        """
            Get configuration, returns cached instance if available otherwise
            builds a new configuration dict.

            Args:
                configs (list): List of configuration dicts
                cache (boolean): True if the result should be cached
        """
        if Configuration.__config:
            return Configuration.__config
        else:
            return Configuration.load_config_stack(configs, cache)

    @staticmethod
    def load_config_stack(configs=None, cache=False):
        """
            load a stack of config dicts into a single dict

            Args:
                configs (list): list of dicts to load
                cache (boolean): True if result should be cached

            Returns: merged dict of all configuration files
        """
        if not configs:
            configs = [LocalConf(DEFAULT_CONFIG), RemoteConf(),
                       LocalConf(SYSTEM_CONFIG), LocalConf(USER_CONFIG),
                       Configuration.__patch]
        else:
            # Handle strings in stack
            for index, item in enumerate(configs):
                if isinstance(item, basestring):
                    configs[index] = LocalConf(item)

        # Merge all configs into one
        base = {}
        for c in configs:
            merge_dict(base, c)

        # copy into cache
        if cache:
            Configuration.__config.clear()
            for key in base:
                Configuration.__config[key] = base[key]
            return Configuration.__config
        else:
            return base

    @staticmethod
    def init(ws):
        """
            Setup websocket handlers to update config.

            Args:
                ws:     Websocket instance
        """
        ws.on("configuration.updated", Configuration.updated)
        ws.on("configuration.patch", Configuration.patch)

    @staticmethod
    def updated(message):
        """
            handler for configuration.updated, triggers an update
            of cached config.
        """
        Configuration.load_config_stack(cache=True)

    @staticmethod
    def patch(message):
        """
            patch the volatile dict usable by skills

            Args:
                message: Messagebus message should contain a config
                         in the data payload.
        """
        config = message.data.get("config", {})
        merge_dict(Configuration.__patch, config)
        Configuration.load_config_stack(cache=True)
