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
"""Common string utilities used by various parts of core."""

import re


def get_http(uri):
    """Change an uri from https:// to http://.
    TODO: Remove as part of 20.08

    Arguments:
        uri: uri to convert

    Returns: (string) uri where https:// has been replaced with http://
    """
    return uri.replace("https://", "http://")


def remove_last_slash(url):
    """Remove the last slash from the given url.
    TODO: Remove as part of 20.08

    Arguments:
        url (str): url to trim

    Returns:
        (str) url without ending slash
    """
    if url and url.endswith('/'):
        url = url[:-1]
    return url


def camel_case_split(identifier: str) -> str:
    """Split camel case string."""
    regex = '.+?(?:(?<=[a-z])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])|$)'
    matches = re.finditer(regex, identifier)
    return ' '.join([m.group(0) for m in matches])
