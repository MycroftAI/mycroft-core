#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
The PyOWM init file

**Author**: Claudio Sparpaglione, @csparpa <csparpa@gmail.com>

**Platform**: platform independent

"""

from pyowm import constants


def OWM(API_key=None, version=constants.LATEST_OWM_API_VERSION,
        config_module=None, language=None, identity=None):
    """
    A parametrized factory method returning a global OWM instance that
    represents the desired OWM web API version (or the currently supported one
    if no version number is specified)

    :param API_key: the OWM web API key (``None`` by default)
    :type API_key: str
    :param version: the OWM web API version. Defaults to ``None``, which means
        use the latest web API version
    :type version: str
    :param config_module: the Python path of the configuration module you want
        to provide for instantiating the library. Defaults to ``None``, which
        means use the default configuration values for the web API version
        support you are currently requesting. Please be aware that malformed
        user-defined configuration modules can lead to unwanted behaviour!
    :type config_module: str (eg: 'mypackage.mysubpackage.myconfigmodule')
    :param language: the language in which you want text results to be
        returned. It's a two-characters string, eg: "en", "ru", "it". Defaults
        to: ``None``, which means use the default language.
    :type language: str
    :returns: an instance of a proper *OWM* subclass
    :raises: *ValueError* when unsupported OWM API versions are provided
    """
    if version == "2.5":
        if config_module is None:
            config_module = (
                "mycroft.skills.weather.owm_repackaged."
                "configuration25_mycroft")
        cfg_module = __import__(config_module,  fromlist=[''])
        from mycroft.skills.weather.owm_repackaged.owm25 import OWM25
        if language is None:
            language = cfg_module.language
        return OWM25(cfg_module.parsers, API_key, cfg_module.cache,
                     language, identity=identity)
    raise ValueError("Unsupported OWM web API version")
