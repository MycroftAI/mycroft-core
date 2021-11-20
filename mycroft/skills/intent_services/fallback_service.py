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
"""Intent service for Mycroft's fallback system."""
from collections import namedtuple
from mycroft.skills.intent_services.base import IntentMatch

FallbackRange = namedtuple('FallbackRange', ['start', 'stop'])


class FallbackService:
    """Intent Service handling fallback skills."""

    def __init__(self, bus):
        self.bus = bus

    def _fallback_range(self, utterances, lang, message, fb_range):
        """Send fallback request for a specified priority range.

        Args:
            utterances (list): List of tuples,
                               utterances and normalized version
            lang (str): Langauge code
            message: Message for session context
            fb_range (FallbackRange): fallback order start and stop.

        Returns:
            IntentMatch or None
        """
        msg = message.reply(
            'mycroft.skills.fallback',
            data={'utterance': utterances[0][0],
                  'lang': lang,
                  'fallback_range': (fb_range.start, fb_range.stop)}
        )
        response = self.bus.wait_for_response(msg, timeout=10)
        if response and response.data['handled']:
            ret = IntentMatch('Fallback', None, {}, None)
        else:
            ret = None
        return ret

    def high_prio(self, utterances, lang, message):
        """Pre-padatious fallbacks."""
        return self._fallback_range(utterances, lang, message,
                                    FallbackRange(0, 5))

    def medium_prio(self, utterances, lang, message):
        """General fallbacks."""
        return self._fallback_range(utterances, lang, message,
                                    FallbackRange(5, 90))

    def low_prio(self, utterances, lang, message):
        """Low prio fallbacks with general matching such as chat-bot."""
        return self._fallback_range(utterances, lang, message,
                                    FallbackRange(90, 101))
