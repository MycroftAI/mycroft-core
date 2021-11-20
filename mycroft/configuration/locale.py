#
# Copyright 2020 Mycroft AI Inc.
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
The mycroft.util.lang module provides the main interface for setting up the
lingua-franca (https://github.com/mycroftai/lingua-franca) selected language
"""
from dateutil.tz import gettz, tzlocal
from mycroft.configuration.config import Configuration

# lingua_franca is optional and might not be installed
# exceptions should only be raised in the parse and format utils


try:
    import lingua_franca as LF
except ImportError:
    LF = None

_lang = "en-us"
_default_tz = None


def get_primary_lang_code():
    if LF:
        return LF.get_primary_lang_code()
    return _lang.split("-")[0]


def get_default_lang():
    if LF:
        return LF.get_default_lang()
    return _lang


def set_default_lang(lang):
    global _lang
    _lang = lang
    if LF:
        LF.set_default_lang(lang)


def get_config_tz():
    config = Configuration.get()
    code = config["location"]["timezone"]["code"]
    return gettz(code)


def get_default_tz():
    # if default was set at runtime use it else use the timezone from .conf
    return _default_tz or get_config_tz()


def set_default_tz(tz=None):
    """ configure LF """
    global _default_tz
    tz = tz or get_config_tz() or tzlocal()
    _default_tz = tz
    if LF:
        # tz added in recently, depends on version
        try:
            LF.time.set_default_tz(tz)
        except:
            pass


def load_languages(langs):
    if LF:
        LF.load_languages(langs)


def load_language(lang):
    if LF:
        LF.load_language(lang)


def setup_locale(lang=None, tz=None):
    lang_code = lang or Configuration.get().get("lang", "en-us")
    # Load language resources, currently en-us must also be loaded at all times
    load_languages([lang_code, "en-us"])
    # Set the active lang to match the configured one
    set_default_lang(lang_code)
    # Set the default timezone to match the configured one
    set_default_tz(tz)


# mycroft-core backwards compat LF only interface
def set_default_lf_lang(lang_code="en-us"):
    """Set the default language of Lingua Franca for parsing and formatting.

    Note: this is a temporary method until a global set_default_lang() method
    can be implemented that updates all Mycroft systems eg STT and TTS.
    It will be deprecated at the earliest possible point.

    Args:
        lang (str): BCP-47 language code, e.g. "en-us" or "es-mx"
    """
    return set_default_lang(lang_code)
