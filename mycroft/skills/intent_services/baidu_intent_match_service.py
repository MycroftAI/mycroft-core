# Copyright 2017 Mycroft AI Inc.
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
from requests.sessions import session
from mycroft.util.log import LOG
from .base import IntentMatch
import uuid
import json
import requests
import traceback


class BaiduIntentMatchService:
    def __init__(self, config):
        LOG.info('[Flow Learning] config == ' + str(config))
        self.config = config
        self.url = None  # config
        self.nlu_service = BaiduNLUService('4bWU5KTBkVXaCefrG8eXCCMQ', 'aYuogapjsGwHLnIfy8G9neAc2RWixwsN')

    def get_skill_id_and_intent_from_intent_str(self, intent_str):
        return None

    def match_intent(self, utterances, _=None, __=None):
        """call Baidu NLU (UNIT) service to search for an matching intent.

        Args:
            utterances (iterable): iterable of utterances, expected order
                                   [raw, normalized, other]

        Returns:
            Intent structure, or None if no match was found.
        """
        LOG.info('[Flow Learning] in match_intent,' + str(utterances))
        LOG.info('[Flow Learning] str(utterances[0])= ' + str(utterances[0]))
        LOG.info('[Flow Learning] str(utterances[0][0])= ' + str(utterances[0][0]))
        response = self.nlu_service.get_response(utterances[0][0], '', None)

        LOG.info('[Flow Learning] response = ' + str(response))
        intent_str = self.nlu_service.get_intent(response)
        LOG.info('intent_str == ' + intent_str)
        skill_id, intent = self.nlu_service.get_id_from_intent_str(intent_str)

        if skill_id is None:
            return None

        reply = self.nlu_service.get_reply(response, intent_str)

        ret = None
        # 'intent_service', 'intent_type', 'intent_data', 'skill_id'
        intent_data = {
            "session_id": response['result']['session_id'],
            "baidu_skill_id": response['result']['response_list'][0]['origin'],
            "reply": reply
        }
        ret = IntentMatch(
                'Baidu_nul', intent, intent_data, skill_id
            )
        LOG.info('[Flow Learning] in BaiduIntentMatchService.match_intent, ret = ' + str(ret))
        LOG.info('[Flow Learning] in BaiduIntentMatchService.match_intent, ret.intent_data["session_id"] , [baidu_skill_id]= ' + str(ret.intent_data['session_id']) + str(ret.intent_data['baidu_skill_id']))
        return ret


class BaiduNLUService:
    def __init__(self, api_key, secret_key):
        self.access_token = None
        self.api_key = api_key
        self.secret_key = secret_key

    def get_token(self):
        if self.access_token is not None:
            return self.access_token
        url = 'https://aip.baidubce.com/oauth/2.0/token'
        params = {'grant_type': 'client_credentials',
              'client_id': self.api_key,
              'client_secret': self.secret_key}
        r = requests.get(url, params=params)
        LOG.info(' response of getting token =' + str(r))
        try:
            r.raise_for_status()
            self.access_token = r.json()['access_token']
            LOG.info(' r.json()[access_token] == ' + str(self.access_token))
            return self.access_token
        except requests.exceptions.HTTPError:
            return self.access_token

    def get_response(self, utterance, baidu_session_id, baidu_skill_id):
        access_token = self.get_token()
        url = 'https://aip.baidubce.com/rpc/2.0/unit/service/chat?access_token=' + access_token
        request = {
            "query": utterance,
            "user_id": "1234567890",
        }
        remembered_skills = []
        if baidu_skill_id is not None:
            remembered_skills.append(baidu_skill_id)
        body = {
            "log_id": str(uuid.uuid1()),
            "version": "2.0",
            "service_id": "S54895",
            "session_id": baidu_session_id,
            "request": request,
            "dialog_state": {
                "contexts": {
                    "SYS_REMEMBERED_SKILLS": remembered_skills
                }
            }
        }
        try:
            headers = {'Content-Type': 'application/json'}
            # Shore
            response = requests.post(url, json=body, headers=headers)
            return json.loads(response.text)
        except Exception:
            # Shore
            LOG.error("in " + traceback.format_exc())
            return None

    def get_reply(self, response, intent):
        reply_for_error = '技能出错，无法正确回复'
        if response is not None and 'result' in response and \
            'response_list' in response['result']:
            response_list = response['result']['response_list']
            if intent == '':
                try:
                    return response_list[0]['action_list'][0]['say']
                except Exception as e:
                    LOG.warning(e)
                    return reply_for_error
            for response in response_list:
                if 'schema' in response and \
                'intent' in response['schema'] and \
                        response['schema']['intent'] == intent:
                    try:
                        return response['action_list'][0]['say']
                    except Exception as e:
                        LOG.warning(e)
                        return reply_for_error
            return reply_for_error
        else:
            return reply_for_error

    def get_intent(self, response):
        # result.response_list[0].schema['intent']
        LOG.info(' in get_intent for baidu UNIT, ' + str(response))
        if response is not None and 'result' in response and 'response_list' in response['result']:
            try:
                return response['result']['response_list'][0]['schema']['intent']
            except Exception as e:
                LOG.warning(e)
                return ''
        else:
            return ''

    def get_slots(self, response):
        pass

    def are_all_slots_satisfied(self, response, intent):
        reply_for_error = '技能出错，无法正确回复'
        str_satisfy = "satisfy"
        if response is not None and 'result' in response and \
            'response_list' in response['result']:
            response_list = response['result']['response_list']
            if intent == '':
                try:
                    return response_list[0]['action_list'][0]['type'] == str_satisfy
                except Exception as e:
                    LOG.warning(e)
                    return False
            for response in response_list:
                if 'schema' in response and \
                'intent' in response['schema'] and \
                        response['schema']['intent'] == intent:
                    try:
                        LOG.info('[Flow Learning] response["action_list"][0]["type"] =' + response['action_list'][0]['type'])
                        return response['action_list'][0]['type'] == str_satisfy
                    except Exception as e:
                        LOG.warning(e)
                        return reply_for_error
            return False
        else:
            return False

    def get_id_from_intent_str(self, intent_str):
        if intent_str == 'WEATHER':
            return 'skill-simple-weather', 'SimpleWeatherIntent.baidu'
        else:
            return None, None
