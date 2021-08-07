# Copyright 2018 Mycroft AI Inc.
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

__author__ = 'seanfitz'
import re
regex_letter_number = r"[a-zA-Z0-9]"
regex_not_letter_number = r"[^a-zA-Z0-9]"
regex_separator = r"[\\?!()\";/\\|`]"

regex_clitics = r"'|:|-|'S|'D|'M|'LL|'RE|'VE|N'T|'s|'d|'m|'ll|'re|'ve|n't"

abbreviations_list = [ "Co.", "Corp.",
            "vs.", "e.g.", "etc.", "ex.", "cf.", "eg.", "Jan.", "Feb.", "Mar.",
            "Apr.", "Jun.", "Jul.", "Aug.", "Sept.", "Oct.", "Nov.", "Dec.",
            "jan.", "feb.", "mar.", "apr.", "jun.", "jul.", "aug.", "sept.",
            "oct.", "nov.", "dec.", "ed.", "eds.", "repr.", "trans.", "vol.",
            "vols.", "rev.", "est.", "b.", "m.", "bur.", "d.", "r.", "M.",
            "Dept.", "MM.", "U.", "Mr.", "Jr.", "Ms.", "Mme.", "Mrs.", "Dr.",
            "Ph.D."]


class EnglishTokenizer(object):
    def __init__(self):
        pass

    def tokenize(self, string):
        """Used to parce a string into tokens

        This function is to take in a string and return a list of tokens

        Args:
            string(str): This is a string of words or a sentance to be parsed into tokens

        Returns:
            list: a list of tokens from the string passed in.

        Notes:
            Doesn't seem to parse contractions correctly for example don't
            would parse as two tokens 'do' and "n't" and this seems to be not
            what we would want.  Maybe should be "don't" or maybe contractions
            should be expanded into "do not" or "do","not".  This could be
            done with a contraction dictionary and some preprocessing.
        """
        s = string
        s = re.sub(r'\t', " ", s)
        s = re.sub(r"(" + regex_separator + ")", r" \g<1> ", s)
        s = re.sub(r"([^0-9]),", r"\g<1> , ", s)
        s = re.sub(r",([^0-9])", r" , \g<1>", s)
        s = re.sub(r"^(')", r"\g<1> ", s)
        s = re.sub(r"(" + regex_not_letter_number + r")'", r"\g<1> '", s)
        s = re.sub(r"(" + regex_clitics + r")$", r" \g<1>", s)
        s = re.sub(r"(" + regex_clitics + r")(" + regex_not_letter_number + r")", r" \g<1> \g<2>", s)

        words = s.strip().split()
        p1 = re.compile(r".*" + regex_letter_number + r"\.")
        p2 = re.compile(r"^([A-Za-z]\.([A-Za-z]\.)+|[A-Z][bcdfghj-nptvxz]+\.)$")

        token_list = []

        for word in words:
            m1 = p1.match(word)
            m2 = p2.match(word)

            if m1 and word not in abbreviations_list and not m2:
                token_list.append(word[0: word.find('.')])
                token_list.append(word[word.find('.')])
            else:
                token_list.append(word)

        return token_list


def tokenize_string(text):
    """To assist with testing strings returns the token list from text

    Args:
        text(str): String to be parsed into tokens

    Returns:
        list: A list of tokens found in the text.
    """
    tk = EnglishTokenizer()
    return tk.tokenize(text)

if __name__ == "__main__":
    print(tokenize_string("Hello world, I'm a happy camper. I don't have any friends?"))
