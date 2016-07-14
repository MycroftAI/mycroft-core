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


from adapt.intent import IntentBuilder
from os.path import dirname, join
from pyowm.exceptions.api_call_error import APICallError
from multi_key_dict import multi_key_dict

import time

from mycroft.identity import IdentityManager
from mycroft.skills.core import MycroftSkill
from mycroft.skills.weather.owm_repackaged import OWM
from mycroft.util.log import getLogger

__author__ = 'jdorleans'

LOGGER = getLogger(__name__)


class WeatherSkill(MycroftSkill):
    def __init__(self):
        super(WeatherSkill, self).__init__(name="WeatherSkill")
        self.temperature = self.config['temperature']
        self.CODES = multi_key_dict()
        self.CODES['01d', '01n'] = 0
        self.CODES['02d', '02n', '03d', '03n'] = 1
        self.CODES['04d', '04n'] = 2
        self.CODES['09d', '09n'] = 3
        self.CODES['10d', '10n'] = 4
        self.CODES['11d', '11n'] = 5
        self.CODES['13d', '13n'] = 6
        self.CODES['50d', '50n'] = 7

    @property
    def owm(self):
        return OWM(API_key=self.config.get('api_key', ''),
                   identity=IdentityManager().get())

    def initialize(self):
        self.load_data_files(dirname(__file__))
        self.__build_current_intent()
        self.__build_next_hour_intent()
        self.__build_next_day_intent()

    def __build_current_intent(self):
        intent = IntentBuilder("CurrentWeatherIntent").require(
            "WeatherKeyword").optionally("Location").build()
        self.register_intent(intent, self.handle_current_intent)

    def __build_next_hour_intent(self):
        intent = IntentBuilder("NextHoursWeatherIntent").require(
            "WeatherKeyword").optionally("Location") \
            .require("NextHours").build()
        self.register_intent(intent, self.handle_next_hour_intent)

    def __build_next_day_intent(self):
        intent = IntentBuilder("NextDayWeatherIntent").require(
            "WeatherKeyword").optionally("Location") \
            .require("NextDay").build()
        self.register_intent(intent, self.handle_next_day_intent)

    def handle_current_intent(self, message):
        try:
            location = message.metadata.get("Location", self.location)
            weather = self.owm.weather_at_place(location).get_weather()
            data = self.__build_data_condition(location, weather)
            weather_code = str(weather.get_weather_icon_name())
            img_code = self.CODES[weather_code]
            temp = data['temp_current']
            self.enclosure.activate_mouth_listeners(False)
            self.enclosure.weather_display(img_code, temp)
            self.speak_dialog('current.weather', data)
            self.__condition_feedback(weather)
            time.sleep(5)
            self.enclosure.activate_mouth_listeners(True)
        except APICallError as e:
            self.__api_error(e)
        except Exception as e:
            LOGGER.debug(e)
            LOGGER.error("Error: {0}".format(e))

    # TODO - Mapping from http://openweathermap.org/weather-conditions
    def __condition_feedback(self, weather):
        status = weather.get_status()
        if status == 'clear':
            self.speak_dialog('sunny.weather')
        elif status == 'rain':
            self.speak_dialog('rain.weather')

    def handle_next_hour_intent(self, message):
        try:
            location = message.metadata.get("Location", self.location)
            weather = self.owm.three_hours_forecast(
                location).get_forecast().get_weathers()[0]
            data = self.__build_data_condition(location, weather)
            weather_code = str(weather.get_weather_icon_name())
            img_code = self.CODES[weather_code]
            temp = data['temp_current']
            self.enclosure.activate_mouth_listeners(False)
            self.enclosure.weather_display(img_code, temp)
            self.speak_dialog('hour.weather', data)
            self.__condition_feedback(weather)
            time.sleep(5)
            self.enclosure.activate_mouth_listeners(True)
        except APICallError as e:
            self.__api_error(e)
        except Exception as e:
            LOGGER.error("Error: {0}".format(e))

    def handle_next_day_intent(self, message):
        try:
            location = message.metadata.get("Location", self.location)
            weather = self.owm.daily_forecast(
                location).get_forecast().get_weathers()[1]
            data = self.__build_data_condition(
                location, weather, 'day', 'min', 'max')
            weather_code = str(weather.get_weather_icon_name())
            img_code = self.CODES[weather_code]
            temp = data['temp_current']
            self.enclosure.activate_mouth_listeners(False)
            self.enclosure.weather_display(img_code, temp)
            self.speak_dialog('tomorrow.weather', data)
            self.__condition_feedback(weather)
            time.sleep(5)
            self.enclosure.activate_mouth_listeners(True)
        except APICallError as e:
            self.__api_error(e)
        except Exception as e:
            LOGGER.error("Error: {0}".format(e))

    def __build_data_condition(
            self, location, weather, temp='temp', temp_min='temp_min',
            temp_max='temp_max'):
        data = {
            'location': location,
            'scale': self.temperature,
            'condition': weather.get_detailed_status(),
            'temp_current': self.__get_temperature(weather, temp),
            'temp_min': self.__get_temperature(weather, temp_min),
            'temp_max': self.__get_temperature(weather, temp_max)
        }
        return data

    def __get_temperature(self, weather, key):
        return str(int(round(weather.get_temperature(self.temperature)[key])))

    def stop(self):
        pass

    def __api_error(self, e):
        LOGGER.error("Error: {0}".format(e))
        if e._triggering_error.code == 401:
            self.speak_dialog('not.paired')


def create_skill():
    return WeatherSkill()
