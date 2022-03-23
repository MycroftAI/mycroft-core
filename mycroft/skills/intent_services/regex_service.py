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
"""An intent parsing service using regular expressions."""
import re

from mycroft.util.log import LOG
from .base import IntentMatch


class RegexService:
    """Intent service using regular expressions."""

    def __init__(self, bus, config):
        self.bus = bus
        self.config = config
        self.patterns = {}

        self.bus.on("regex:register_intent", self.register_intent)

    def register_intent(self, message):
        name = message.data["name"]
        pattern = message.data["pattern"]

        compiled_pattern = re.compile(pattern)
        self.patterns[name] = compiled_pattern
        LOG.info("Registered regex intent: %s", compiled_pattern.pattern)

    def match_intent(self, utterances, _=None, __=None):
        """Run regex matches.

        Args:
            utterances (iterable): utterances for consideration in intent
            matching. As a practical matter, a single utterance will be
            passed in most cases.  But there are instances, such as
            streaming STT that could pass multiple.  Each utterance
            is represented as a tuple containing the raw, normalized, and
            possibly other variations of the utterance.

        Returns:
            Intent structure, or None if no match was found.
        """
        for name, pattern in self.patterns.items():
            for utt in utterances:
                for variant in utt:
                    match = pattern.match(variant)
                    if match:
                        LOG.info("'%s' matched %s", variant, pattern.pattern)
                        skill_id = name.split(":")[0]
                        return IntentMatch("regex", name, match.groupdict(), skill_id)

        return None
