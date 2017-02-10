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

from adapt.intent import IntentBuilder
from multi_key_dict import multi_key_dict
from os.path import dirname
from pyowm import OWM
from pyowm.webapi25.forecaster import Forecaster
from pyowm.webapi25.forecastparser import ForecastParser
from pyowm.webapi25.observationparser import ObservationParser
from requests import HTTPError

from mycroft.api import Api
from mycroft.messagebus.message import Message
from mycroft.skills.core import MycroftSkill
from mycroft.util.log import getLogger

__author__ = 'jdorleans'

LOG = getLogger(__name__)


class OWMApi(Api):
    def __init__(self):
        super(OWMApi, self).__init__("owm")
        self.lang = "en"
        self.observation = ObservationParser()
        self.forecast = ForecastParser()

    def build_query(self, params):
        params.get("query").update({"lang": self.lang})
        return params.get("query")

    def get_data(self, response):
        return response.text

    def weather_at_place(self, name):
        data = self.request({
            "path": "/weather",
            "query": {"q": name}
        })
        return self.observation.parse_JSON(data)

    def three_hours_forecast(self, name):
        data = self.request({
            "path": "/forecast",
            "query": {"q": name}
        })
        return self.to_forecast(data, "3h")

    def daily_forecast(self, name, limit=None):
        query = {"q": name}
        if limit is not None:
            query["cnt"] = limit
        data = self.request({
            "path": "/forecast/daily",
            "query": query
        })
        return self.to_forecast(data, "daily")

    def to_forecast(self, data, interval):
        forecast = self.forecast.parse_JSON(data)
        if forecast is not None:
            forecast.set_interval(interval)
            return Forecaster(forecast)
        else:
            return None


class WeatherSkill(MycroftSkill):
    def __init__(self):
        super(WeatherSkill, self).__init__("WeatherSkill")
        self.temperature = self.config.get('temperature')
        self.__init_owm()
        self.CODES = multi_key_dict()
        self.CODES['01d', '01n'] = 0
        self.CODES['02d', '02n', '03d', '03n'] = 1
        self.CODES['04d', '04n'] = 2
        self.CODES['09d', '09n'] = 3
        self.CODES['10d', '10n'] = 4
        self.CODES['11d', '11n'] = 5
        self.CODES['13d', '13n'] = 6
        self.CODES['50d', '50n'] = 7

    def __init_owm(self):
        key = self.config.get('api_key')
        if key and not self.config.get('proxy'):
            self.owm = OWM(key)
        else:
            self.owm = OWMApi()

    def initialize(self):
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
            location, pretty_location = self.get_location(message)

            weather = self.owm.weather_at_place(location).get_weather()
            data = self.__build_data_condition(pretty_location, weather)

            # BUG:  OWM is commonly reporting incorrect high/low data in the
            # "current" request.  So grab that from the forecast API call.
            weather_forecast = self.owm.three_hours_forecast(
                location).get_forecast().get_weathers()[0]
            data_forecast = self.__build_data_condition(pretty_location,
                                                        weather_forecast)
            data["temp_min"] = data_forecast["temp_min"]
            data["temp_max"] = data_forecast["temp_max"]

            weather_code = str(weather.get_weather_icon_name())
            img_code = self.CODES[weather_code]
            temp = data['temp_current']
            self.enclosure.deactivate_mouth_events()
            self.enclosure.weather_display(img_code, temp)

            dialog_name = "current"
            if pretty_location == self.location_pretty:
                dialog_name += ".local"
            self.speak_dialog(dialog_name+".weather", data)

            time.sleep(5)
            self.enclosure.activate_mouth_events()
        except HTTPError as e:
            self.__api_error(e)
        except Exception as e:
            LOG.error("Error: {0}".format(e))

    def handle_next_hour_intent(self, message):
        try:
            location, pretty_location = self.get_location(message)
            weather = self.owm.three_hours_forecast(
                location).get_forecast().get_weathers()[0]
            data = self.__build_data_condition(pretty_location, weather)
            weather_code = str(weather.get_weather_icon_name())
            img_code = self.CODES[weather_code]
            temp = data['temp_current']
            self.enclosure.deactivate_mouth_events()
            self.enclosure.weather_display(img_code, temp)
            if pretty_location == self.location_pretty:
                self.speak_dialog('hour.weather', data)
            else:
                self.speak_dialog('hour.weather', data)
            time.sleep(5)
            self.enclosure.activate_mouth_events()
        except HTTPError as e:
            self.__api_error(e)
        except Exception as e:
            LOG.error("Error: {0}".format(e))

    def handle_next_day_intent(self, message):
        try:
            location, pretty_location = self.get_location(message)
            weather = self.owm.daily_forecast(
                location).get_forecast().get_weathers()[1]
            data = self.__build_data_condition(
                pretty_location, weather, 'day', 'min', 'max')
            weather_code = str(weather.get_weather_icon_name())
            img_code = self.CODES[weather_code]
            temp = data['temp_current']
            self.enclosure.deactivate_mouth_events()
            self.enclosure.weather_display(img_code, temp)
            if pretty_location == self.location_pretty:
                self.speak_dialog('tomorrow.local.weather', data)
            else:
                self.speak_dialog('tomorrow.weather', data)
            time.sleep(5)
            self.enclosure.activate_mouth_events()
        except HTTPError as e:
            self.__api_error(e)
        except Exception as e:
            LOG.error("Error: {0}".format(e))

    def get_location(self, message):
        try:
            location = message.data.get("Location", None)
            if location:
                return location, location

            location = self.location
            if type(location) is dict:
                city = location["city"]
                state = city["state"]
                return city["name"] + ", " + state["name"] + ", " + \
                    state["country"]["name"], self.location_pretty

            return None
        except:
            self.speak_dialog("location.not.found")
            raise ValueError("Location not found")

    def __build_data_condition(
            self, location_pretty, weather, temp='temp', temp_min='temp_min',
            temp_max='temp_max'):

        data = {
            'location': location_pretty,
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
        if e.response.status_code == 401:
            self.emitter.emit(Message("mycroft.not.paired"))


def create_skill():
    return WeatherSkill()
