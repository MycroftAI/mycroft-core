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


from pyowm.caches import nullcache
from pyowm.webapi25 import observationparser
from pyowm.webapi25 import observationlistparser
from pyowm.webapi25 import forecastparser
from pyowm.webapi25 import weatherhistoryparser
from pyowm.webapi25 import stationparser
from pyowm.webapi25 import stationlistparser
from pyowm.webapi25 import stationhistoryparser
from pyowm.webapi25 import weathercoderegistry
from pyowm.webapi25 import cityidregistry

from mycroft.configuration.config import ConfigurationManager

"""
Configuration for the PyOWM library specific to OWM web API version 2.5
"""

config = ConfigurationManager.get().get('WeatherSkill')

if config.get('api_key'):
    ROOT_API_URL = 'http://api.openweathermap.org/data/2.5'
else:
    ROOT_API_URL = 'https://cerberus.mycroft.ai/weather/owm'

# OWM web API URLs
ICONS_BASE_URL = 'http://openweathermap.org/img/w'
OBSERVATION_URL = ROOT_API_URL + '/weather'
STATION_URL = ROOT_API_URL + '/station'
FIND_OBSERVATIONS_URL = ROOT_API_URL + '/find'
FIND_STATION_URL = ROOT_API_URL + '/station/find'
BBOX_STATION_URL = ROOT_API_URL + '/box/station'
THREE_HOURS_FORECAST_URL = ROOT_API_URL + '/forecast'
DAILY_FORECAST_URL = ROOT_API_URL + '/forecast/daily'
CITY_WEATHER_HISTORY_URL = ROOT_API_URL + '/history/city'
STATION_WEATHER_HISTORY_URL = ROOT_API_URL + '/history/station'

# Parser objects injection for OWM web API responses parsing
parsers = {
  'observation': observationparser.ObservationParser(),
  'observation_list': observationlistparser.ObservationListParser(),
  'forecast': forecastparser.ForecastParser(),
  'weather_history': weatherhistoryparser.WeatherHistoryParser(),
  'station_history': stationhistoryparser.StationHistoryParser(),
  'station': stationparser.StationParser(),
  'station_list': stationlistparser.StationListParser(),
}

# City ID registry
city_id_registry = cityidregistry.CityIDRegistry('cityids/%03d-%03d.txt')

# Cache provider to be used
cache = nullcache.NullCache()

# Default language for OWM web API queries text results
language = 'en'

# OWM web API availability test timeout in seconds
API_AVAILABILITY_TIMEOUT = 2

# Weather status code registry
weather_code_registry = weathercoderegistry.WeatherCodeRegistry({
    "rain": [{
        "start": 500,
        "end": 531
    }, {
        "start": 300,
        "end": 321
    }],
    "sun": [{
        "start": 800,
        "end": 800
    }],
    "clouds": [{
        "start": 801,
        "end": 804
    }],
    "fog": [{
        "start": 741,
        "end": 741
    }],
    "haze": [{
        "start": 721,
        "end": 721
    }],
    "mist": [{
        "start": 701,
        "end": 701
    }],
    "snow": [{
        "start": 600,
        "end": 622
    }],
    "tornado": [{
        "start": 781,
        "end": 781
    }, {
        "start": 900,
        "end": 900
    }],
    "storm": [{
        "start": 901,
        "end": 901
    }, {
        "start": 960,
        "end": 961
    }],
    "hurricane": [{
        "start": 902,
        "end": 902
    }, {
        "start": 962,
        "end": 962
    }]
})
