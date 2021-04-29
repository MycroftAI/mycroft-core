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

from lingua_franca.lang import set_default_lang as _set_default_lf_lang

import mycroft.configuration


def get_default_lang():
    """Get the default language from the Mycroft configuration.

    Note: Currently STT and TTS engines have their own language configurations
          which do not operate off this default language.
    """
    # return "en-us"
    config = mycroft.configuration.Configuration.get()
    return config.get("lang", "en-us")


def set_default_lf_lang(lang_code="en-us"):
    """Set the default language of Lingua Franca for parsing and formatting.

    Args:
        lang (str): BCP-47 language code, e.g. "en-us" or "es-mx"
    """
    return _set_default_lf_lang(lang_code=lang_code)
