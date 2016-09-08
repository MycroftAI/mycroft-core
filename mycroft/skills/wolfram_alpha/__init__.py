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


from StringIO import StringIO

import re
import requests
import wolframalpha
from os.path import dirname, join
from six.moves import urllib

from mycroft.identity import IdentityManager
from mycroft.skills.core import MycroftSkill
from mycroft.util import CerberusAccessDenied
from mycroft.util.log import getLogger

__author__ = 'seanfitz'

logger = getLogger(__name__)


class EnglishQuestionParser(object):
    """
    Poor-man's english question parser. Not even close to conclusive, but
    appears to construct some decent w|a queries and responses.
    """

    def __init__(self):
        self.regexes = [
            re.compile(
                ".*(?P<QuestionWord>who|what|when|where|why|which) "
                "(?P<Query1>.*) (?P<QuestionVerb>is|are|was|were) "
                "(?P<Query2>.*)"),
            re.compile(
                ".*(?P<QuestionWord>what)(?P<QuestionVerb>\'s|s) "
                "(?P<Query>.*)"),
            re.compile(
                ".*(?P<QuestionWord>who|what|when|where|why|which) "
                "(?P<QuestionVerb>\w+) (?P<Query>.*)")
        ]

    def _normalize(self, groupdict):
        if 'Query' in groupdict:
            return groupdict
        elif 'Query1' and 'Query2' in groupdict:
            return {
                'QuestionWord': groupdict.get('QuestionWord'),
                'QuestionVerb': groupdict.get('QuestionVerb'),
                'Query': ' '.join([groupdict.get('Query1'), groupdict.get(
                    'Query2')])
            }

    def parse(self, utterance):
        for regex in self.regexes:
            match = regex.match(utterance)
            if match:
                return self._normalize(match.groupdict())
        return None


class CerberusWolframAlphaClient(object):
    """
    Wolfram|Alpha v2.0 client
    """

    def query(self, query):
        """
        Query Wolfram|Alpha with query using the v2.0 API
        """
        identity = IdentityManager.get()
        query = urllib.parse.urlencode(dict(input=query))
        url = 'https://cerberus.mycroft.ai/wolframalpha/v2/query?' + query
        headers = {'Authorization': 'Bearer ' + identity.token}
        response = requests.get(url, headers=headers)
        if response.status_code == 401:
            raise CerberusAccessDenied()
        return wolframalpha.Result(StringIO(response.content))


class WolframAlphaSkill(MycroftSkill):
    def __init__(self):
        MycroftSkill.__init__(self, name="WolframAlphaSkill")
        self.__init_client()
        self.question_parser = EnglishQuestionParser()

    def __init_client(self):
        key = self.config.get('api_key')
        if key:
            self.client = wolframalpha.Client(key)
        else:
            self.client = CerberusWolframAlphaClient()

    def initialize(self):
        self.init_dialog(dirname(__file__))
        self.emitter.on('intent_failure', self.handle_fallback)

    def get_result(self, res):
        result = None
        try:
            result = next(res.results).text
            return result
        except:
            try:
                result = self.__find_pod_id(res.pods, 'Value')
                if not result:
                    result = self.__find_pod_id(
                        res.pods, 'NotableFacts:PeopleData')
                    if not result:
                        result = self.__find_pod_id(
                            res.pods, 'BasicInformation:PeopleData')
                        if not result:
                            result = self.__find_pod_id(res.pods, 'Definition')
                            if not result:
                                result = self.__find_pod_id(
                                    res.pods, 'DecimalApproximation')
                                if result:
                                    result = result[:5]
                                else:
                                    result = self.__find_num(
                                        res.pods, '200')
                return result
            except:
                return result

    def handle_fallback(self, message):
        self.enclosure.mouth_think()
        logger.debug(
            "Could not determine intent, falling back to WolframAlpha Skill!")
        utterance = message.data.get('utterance')
        parsed_question = self.question_parser.parse(utterance)

        query = utterance
        if parsed_question:
            # Try to store pieces of utterance (None if not parsed_question)
            utt_word = parsed_question.get('QuestionWord')
            utt_verb = parsed_question.get('QuestionVerb')
            utt_query = parsed_question.get('Query')
            if utt_verb == "'s":
                utt_verb = 'is'
                parsed_question['QuestionVerb'] = 'is'
            query = "%s %s %s" % (utt_word, utt_verb, utt_query)
            phrase = "know %s %s %s" % (utt_word, utt_query, utt_verb)
        else:  # TODO: Localization
            phrase = "understand the phrase " + utterance

        try:
            res = self.client.query(query)
            result = self.get_result(res)
            others = self._find_did_you_mean(res)
        except CerberusAccessDenied as e:
            self.speak_dialog('not.paired')
            return
        except Exception as e:
            logger.exception(e)
            self.speak_dialog("not.understood", data={'phrase': phrase})
            return

        if result:
            input_interpretation = self.__find_pod_id(res.pods, 'Input')
            verb = "is"
            structured_syntax_regex = re.compile(".*(\||\[|\\\\|\]).*")
            if parsed_question:
                if not input_interpretation or structured_syntax_regex.match(
                        input_interpretation):
                    input_interpretation = parsed_question.get('Query')
                verb = parsed_question.get('QuestionVerb')

            if "|" in result:  # Assuming "|" indicates a list of items
                verb = ":"

            result = self.process_wolfram_string(result)
            input_interpretation = \
                self.process_wolfram_string(input_interpretation)
            response = "%s %s %s" % (input_interpretation, verb, result)

            self.speak(response)
        else:
            if len(others) > 0:
                self.speak_dialog('others.found',
                                  data={'utterance': utterance, 'alternative':
                                      others[0]})
            else:
                self.speak_dialog("not.understood", data={'phrase': phrase})

    @staticmethod
    def __find_pod_id(pods, pod_id):
        for pod in pods:
            if pod_id in pod.id:
                return pod.text
        return None

    @staticmethod
    def __find_num(pods, pod_num):
        for pod in pods:
            if pod.node.attrib['position'] == pod_num:
                return pod.text
        return None

    @staticmethod
    def _find_did_you_mean(res):
        value = []
        root = res.tree.find('didyoumeans')
        if root is not None:
            for result in root:
                value.append(result.text)
        return value

    def process_wolfram_string(self, text):
        # Remove extra whitespace
        text = re.sub(r" \s+", r" ", text)

        # Convert | symbols to commas
        text = re.sub(r" \| ", r", ", text)

        # Convert newlines to commas
        text = re.sub(r"\n", r", ", text)

        # Convert !s to factorial
        text = re.sub(r"!", r",factorial", text)

        with open(join(dirname(__file__), 'regex',
                       self.lang, 'list.rx'), 'r') as regex:
            list_regex = re.compile(regex.readline())

        match = list_regex.match(text)
        if match:
            text = match.group('Definition')

        return text

    def stop(self):
        pass


def create_skill():
    return WolframAlphaSkill()
