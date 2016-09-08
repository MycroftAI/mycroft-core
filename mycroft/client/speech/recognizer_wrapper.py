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

import requests
from speech_recognition import UnknownValueError

from mycroft.configuration import ConfigurationManager
from mycroft.identity import IdentityManager
from mycroft.metrics import Stopwatch
from mycroft.util import CerberusAccessDenied
from mycroft.util.log import getLogger
from mycroft.util.setup_base import get_version

__author__ = 'seanfitz'

log = getLogger("RecognizerWrapper")

config = ConfigurationManager.get().get('speech_client')


class GoogleRecognizerWrapper(object):
    def __init__(self, recognizer):
        self.recognizer = recognizer

    def transcribe(
            self, audio, language="en-US", show_all=False, metrics=None):
        key = config.get('credential').get("token")
        return self.recognizer.recognize_google(
            audio, key=key, language=language, show_all=show_all)


class WitRecognizerWrapper(object):
    def __init__(self, recognizer):
        self.recognizer = recognizer

    def transcribe(
            self, audio, language="en-US", show_all=False, metrics=None):
        assert language == "en-US", \
            "language must be default, language parameter not supported."
        key = config.get('credential').get("token")
        return self.recognizer.recognize_wit(audio, key, show_all=show_all)


class IBMRecognizerWrapper(object):
    def __init__(self, recognizer):
        self.recognizer = recognizer

    def transcribe(
            self, audio, language="en-US", show_all=False, metrics=None):
        credential = config.get('credential')
        username = credential.get('username')
        password = credential.get('password')
        return self.recognizer.recognize_ibm(
            audio, username, password, language=language, show_all=show_all)


class MycroftRecognizer(object):
    def __init__(self, _):
        self.version = get_version()

    def transcribe(
            self, audio, language="en-US", show_all=False, metrics=None):

        # FIXME - Refactor
        raise CerberusAccessDenied()

        timer = Stopwatch()
        timer.start()
        identity = IdentityManager.get()
        headers = {'Authorization': 'Bearer ' + identity.token}
        url = ConfigurationManager.get().get("server").get("url")
        response = requests.post(url +
                                 "/stt/google_v2?language=%s&version=%s"
                                 % (language, self.version),
                                 audio.get_flac_data(),
                                 headers=headers)
        if metrics:
            t = timer.stop()
            metrics.timer("mycroft.cerberus.proxy.client.time_s", t)
            metrics.timer("mycroft.stt.remote.time_s", t)

        if response.status_code == 401:
            raise CerberusAccessDenied()

        try:
            actual_result = response.json()
        except:
            raise UnknownValueError()

        log.info("STT JSON: " + json.dumps(actual_result))
        if show_all:
            return actual_result

        # return the best guess
        if "alternative" not in actual_result:
            raise UnknownValueError()
        alternatives = actual_result["alternative"]
        if len([alt for alt in alternatives if alt.get('confidence')]) > 0:
            # if there is at least one element with confidence, force it to
            # the front
            alternatives.sort(
                key=lambda e: e.get('confidence', 0.0), reverse=True)

        for entry in alternatives:
            if "transcript" in entry:
                return entry["transcript"]

        if len(alternatives) > 0:
            log.error(
                "Found %d entries, but none with a transcript." % len(
                    alternatives))

        # no transcriptions available
        raise UnknownValueError()


RECOGNIZER_IMPLS = {
    'mycroft': MycroftRecognizer,
    'google': GoogleRecognizerWrapper,
    'wit': WitRecognizerWrapper,
    'ibm': IBMRecognizerWrapper
}


class RemoteRecognizerWrapperFactory(object):
    @staticmethod
    def wrap_recognizer(recognizer, impl=config.get('module')):
        if impl not in RECOGNIZER_IMPLS.keys():
            raise NotImplementedError("%s recognizer not implemented." % impl)

        impl_class = RECOGNIZER_IMPLS.get(impl)
        return impl_class(recognizer)
