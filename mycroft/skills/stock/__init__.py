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

import time
import xml.etree.ElementTree as ET

import requests
from adapt.intent import IntentBuilder
from os.path import dirname

from mycroft.skills.core import MycroftSkill
from mycroft.util.log import getLogger

__author__ = 'eward'
logger = getLogger(__name__)


class StockSkill(MycroftSkill):
    def __init__(self):
        super(StockSkill, self).__init__(name="StockSkill")

    def initialize(self):
        self.load_data_files(dirname(__file__))

        stock_price_intent = IntentBuilder("StockPriceIntent") \
            .require("StockPriceKeyword").require("Company").build()
        self.register_intent(stock_price_intent,
                             self.handle_stock_price_intent)

    def handle_stock_price_intent(self, message):
        company = message.data.get("Company")
        try:
            response = self.find_and_query(company)
            self.emitter.once("recognizer_loop:audio_output_start",
                              self.enclosure.mouth_text(
                                  response['symbol'] + ": " + response[
                                      'price']))
            self.enclosure.activate_mouth_listeners(False)
            self.speak_dialog("stock.price", data=response)
            time.sleep(12)
            self.enclosure.activate_mouth_listeners(True)
            self.enclosure.mouth_reset()

        except:
            self.speak_dialog("not.found", data={'company': company})

    def _query(self, url, param_name, query):
        payload = {param_name: query}
        response = requests.get(url, params=payload)
        return ET.fromstring(response.content)

    def find_and_query(self, query):
        root = self._query(
            "http://dev.markitondemand.com/MODApis/Api/v2/Lookup?",
            'input', query)
        root = self._query(
            "http://dev.markitondemand.com/Api/v2/Quote?", 'symbol',
            root.iter('Symbol').next().text)
        return {'symbol': root.iter('Symbol').next().text,
                'company': root.iter('Name').next().text,
                'price': root.iter('LastPrice').next().text}

    def stop(self):
        pass


def create_skill():
    return StockSkill()
