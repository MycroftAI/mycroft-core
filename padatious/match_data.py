# Copyright 2017 Mycroft AI, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


class MatchData(object):
    """
    A set of data describing how a query fits into an intent

    Attributes:
        name (str): Name of matched intent
        sent (str): The query after entity extraction
        conf (float): Confidence (from 0.0 to 1.0)
        matches (dict of str -> str): Key is the name of the entity and
            value is the extracted part of the sentence
    """
    def __init__(self, name, sent, matches=None, conf=0.0):
        self.name = name
        self.sent = sent
        self.matches = matches or {}
        self.conf = conf

    def __getitem__(self, item):
        return self.matches.__getitem__(item)

    def __contains__(self, item):
        return self.matches.__contains__(item)

    def get(self, key, default=None):
        return self.matches.get(key, default)

    def __repr__(self):
        return repr(self.__dict__)

    @staticmethod
    def handle_apostrophes(old_sentence):
        """
        Attempts to handle utterances with apostrophes in them
        """
        new_sentence = ''
        apostrophe_present = False
        for word in old_sentence:
            if word == "'":
                apostrophe_present = True
                new_sentence += word
            else:
                # If the apostrophe is present we don't want to add
                # a whitespace after the apostrophe
                if apostrophe_present:
                    # If the word after the apostrophe is longer than a character long assume that
                    # the previous word is an "s" + apostrophe instead of "word + apostrophe
                    if len(word) > 1:
                        new_sentence += " " + word
                    else:
                        new_sentence += word
                        apostrophe_present = False
                else:
                    if len(new_sentence) > 0:
                        new_sentence += " " + word
                    else:
                        new_sentence = word
        return new_sentence
    # Converts parameters from lists of tokens to one combined string
    def detokenize(self):
        self.sent = self.handle_apostrophes(self.sent)

        new_matches = {}
        for token, sent in self.matches.items():
            new_token = token.replace('{', '').replace('}', '')
            new_matches[new_token] = self.handle_apostrophes(sent)
        self.matches = new_matches
