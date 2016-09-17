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


"""
Module containing classes for HTTP client/server interactions
"""

# Python 2.x/3.x compatibility imports
try:
    from urllib.error import HTTPError, URLError
    from urllib.parse import urlencode
except ImportError:
    from urllib2 import HTTPError, URLError
    from urllib import urlencode

import socket

from pyowm.exceptions import api_call_error


class OWMHTTPClient(object):
    """
    An HTTP client class, that can leverage a cache mechanism.

    :param API_key: a Unicode object representing the OWM web API key
    :type API_key: Unicode
    :param cache: an *OWMCache* concrete instance that will be used to
         cache OWM web API responses.
    :type cache: an *OWMCache* concrete instance

    """

    def __init__(self, API_key, cache, identity):
        self._API_key = API_key
        self._cache = cache
        self._identity = identity

    def call_API(self, API_endpoint_URL, params_dict,
                 timeout=socket._GLOBAL_DEFAULT_TIMEOUT):

        """
        Invokes a specific OWM web API endpoint URL, returning raw JSON data.

        :param API_endpoint_URL: the API endpoint to be invoked
        :type API_endpoint_URL: str
        :param params_dict: a dictionary containing the query parameters to be
            used in the HTTP request (given as key-value couples in the dict)
        :type params_dict: dict
        :param timeout: how many seconds to wait for connection establishment
            (defaults to ``socket._GLOBAL_DEFAULT_TIMEOUT``)
        :type timeout: int
        :returns: a string containing raw JSON data
        :raises: *APICallError*

        """
        url = self._build_full_URL(API_endpoint_URL, params_dict)
        cached = self._cache.get(url)
        if cached:
            return cached
        else:
            try:
                if self._identity and self._identity.token:
                    bearer_token_header = "Bearer " + self._identity.token
                else:
                    bearer_token_header = None
                try:
                    from urllib.request import build_opener
                    opener = build_opener()
                    if bearer_token_header:
                        opener.addheaders = [
                            ('Authorization', bearer_token_header)]
                except ImportError:
                    from urllib2 import build_opener
                    opener = build_opener()
                    if bearer_token_header:
                        opener.addheaders = [
                            ('Authorization', bearer_token_header)]
                response = opener.open(url, None, timeout)
            except HTTPError as e:
                raise api_call_error.APICallError(str(e.reason), e)
            except URLError as e:
                raise api_call_error.APICallError(str(e.reason), e)
            else:
                data = response.read().decode('utf-8')
                self._cache.set(url, data)
                return data

    def _build_full_URL(self, API_endpoint_URL, params_dict):
        """
        Adds the API key and the query parameters dictionary to the specified
        API endpoint URL, returning a complete HTTP request URL.

        :param API_endpoint_URL: the API endpoint base URL
        :type API_endpoint_URL: str
        :param params_dict: a dictionary containing the query parameters to be
            used in the HTTP request (given as key-value couples in the dict)
        :type params_dict: dict
        :param API_key: the OWM web API key
        :type API_key: str
        :returns: a full string HTTP request URL

        """
        params = params_dict.copy()
        if self._API_key is not None:
            params['APPID'] = self._API_key
        return self._build_query_parameters(API_endpoint_URL, params)

    def _build_query_parameters(self, base_URL, params_dict):
        """
        Turns dictionary items into query parameters and adds them to the base
        URL

        :param base_URL: the base URL whom the query parameters must be added
            to
        :type base_URL: str
        :param params_dict: a dictionary containing the query parameters to be
            used in the HTTP request (given as key-value couples in the dict)
        :type params_dict: dict
        :returns: a full string HTTP request URL

        """
        return base_URL + '?' + urlencode(params_dict)

    def __repr__(self):
        return "<%s.%s - cache=%s>" % \
               (__name__, self.__class__.__name__, repr(self._cache))
