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

"""
The mycroft.util.format module provides various formatting functions for
things like numbers, times, etc.

The focus of these formatting functions is to create natural sounding speech
and allow localization.
"""
import json
import os
import datetime
import re
import warnings

from collections import namedtuple
from calendar import leapdays
from enum import Enum

from mycroft.util.lang import get_full_lang_code, get_primary_lang_code

from mycroft.util.lang.format_en import *
from mycroft.util.lang.format_pt import *
from mycroft.util.lang.format_it import *
from mycroft.util.lang.format_sv import *
from mycroft.util.lang.format_hu import *

from mycroft.util.lang.format_es import nice_number_es
from mycroft.util.lang.format_es import nice_time_es
from mycroft.util.lang.format_es import pronounce_number_es
from mycroft.util.lang.format_de import nice_number_de
from mycroft.util.lang.format_de import nice_time_de
from mycroft.util.lang.format_de import pronounce_number_de
from mycroft.util.lang.format_fr import nice_number_fr
from mycroft.util.lang.format_fr import nice_time_fr
from mycroft.util.lang.format_fr import pronounce_number_fr
from mycroft.util.lang.format_nl import nice_time_nl
from mycroft.util.lang.format_nl import pronounce_number_nl
from mycroft.util.lang.format_nl import nice_number_nl
from mycroft.util.lang.format_da import nice_number_da
from mycroft.util.lang.format_da import nice_time_da
from mycroft.util.lang.format_da import pronounce_number_da

from padatious.util import expand_parentheses


def _translate_word(name, lang):
    """ Helper to get word tranlations

    Args:
        name (str): Word name. Returned as the default value if not translated.
        lang (str): Language code, e.g. "en-us"

    Returns:
        str: translated version of resource name
    """
    from mycroft.util import resolve_resource_file

    lang_code = get_full_lang_code(lang)

    filename = resolve_resource_file(
        os.path.join("text", lang_code, name+".word"))
    if filename:
        # open the file
        try:
            with open(filename, 'r', encoding='utf8') as f:
                for line in f:
                    word = line.strip()
                    if word.startswith("#"):
                        continue  # skip comment lines
                    return word
        except Exception:
            pass
    return name  # use resource name as the word


NUMBER_TUPLE = namedtuple(
    'number',
    ('x, xx, x0, x_in_x0, xxx, x00, x_in_x00, xx00, xx_in_xx00, x000, ' +
     'x_in_x000, x0_in_x000, x_in_0x00'))


class TimeResolution(Enum):
    YEARS = 1
    DAYS = 2
    HOURS = 3
    MINUTES = 4
    SECONDS = 5
    MILLISECONDS = 6


class DateTimeFormat:
    def __init__(self, config_path):
        self.lang_config = {}
        self.config_path = config_path

    def cache(self, lang):
        if lang not in self.lang_config:
            try:
                # Attempt to load the language-specific formatting data
                with open(self.config_path + '/' + lang + '/date_time.json',
                          'r') as lang_config_file:
                    self.lang_config[lang] = json.loads(
                        lang_config_file.read())
            except FileNotFoundError:
                # Fallback to English formatting
                with open(self.config_path + '/en-us/date_time.json',
                          'r') as lang_config_file:
                    self.lang_config[lang] = json.loads(
                        lang_config_file.read())

            for x in ['decade_format', 'hundreds_format', 'thousand_format',
                      'year_format']:
                i = 1
                while self.lang_config[lang][x].get(str(i)):
                    self.lang_config[lang][x][str(i)]['re'] = (
                        re.compile(self.lang_config[lang][x][str(i)]['match']
                                   ))
                    i = i + 1

    def _number_strings(self, number, lang):
        x = (self.lang_config[lang]['number'].get(str(number % 10)) or
             str(number % 10))
        xx = (self.lang_config[lang]['number'].get(str(number % 100)) or
              str(number % 100))
        x_in_x0 = self.lang_config[lang]['number'].get(
            str(int(number % 100 / 10))) or str(int(number % 100 / 10))
        x0 = (self.lang_config[lang]['number'].get(
            str(int(number % 100 / 10) * 10)) or
            str(int(number % 100 / 10) * 10))
        xxx = (self.lang_config[lang]['number'].get(str(number % 1000)) or
               str(number % 1000))
        x00 = (self.lang_config[lang]['number'].get(str(int(
            number % 1000 / 100) * 100)) or
            str(int(number % 1000 / 100) * 100))
        x_in_x00 = self.lang_config[lang]['number'].get(str(int(
            number % 1000 / 100))) or str(int(number % 1000 / 100))
        xx00 = self.lang_config[lang]['number'].get(str(int(
            number % 10000 / 100) * 100)) or str(int(number % 10000 / 100) *
                                                 100)
        xx_in_xx00 = self.lang_config[lang]['number'].get(str(int(
            number % 10000 / 100))) or str(int(number % 10000 / 100))
        x000 = (self.lang_config[lang]['number'].get(str(int(
            number % 10000 / 1000) * 1000)) or
            str(int(number % 10000 / 1000) * 1000))
        x_in_x000 = self.lang_config[lang]['number'].get(str(int(
            number % 10000 / 1000))) or str(int(number % 10000 / 1000))
        x0_in_x000 = self.lang_config[lang]['number'].get(str(int(
            number % 10000 / 1000)*10)) or str(int(number % 10000 / 1000)*10)
        x_in_0x00 = self.lang_config[lang]['number'].get(str(int(
            number % 1000 / 100)) or str(int(number % 1000 / 100)))

        return NUMBER_TUPLE(
            x, xx, x0, x_in_x0, xxx, x00, x_in_x00, xx00, xx_in_xx00, x000,
            x_in_x000, x0_in_x000, x_in_0x00)

    def _format_string(self, number, format_section, lang):
        s = self.lang_config[lang][format_section]['default']
        i = 1
        while self.lang_config[lang][format_section].get(str(i)):
            e = self.lang_config[lang][format_section][str(i)]
            if e['re'].match(str(number)):
                return e['format']
            i = i + 1
        return s

    def _decade_format(self, number, number_tuple, lang):
        s = self._format_string(number % 100, 'decade_format', lang)
        return s.format(x=number_tuple.x, xx=number_tuple.xx,
                        x0=number_tuple.x0, x_in_x0=number_tuple.x_in_x0,
                        number=str(number % 100))

    def _number_format_hundreds(self, number, number_tuple, lang,
                                formatted_decade):
        s = self._format_string(number % 1000, 'hundreds_format', lang)
        return s.format(xxx=number_tuple.xxx, x00=number_tuple.x00,
                        x_in_x00=number_tuple.x_in_x00,
                        formatted_decade=formatted_decade,
                        number=str(number % 1000))

    def _number_format_thousand(self, number, number_tuple, lang,
                                formatted_decade, formatted_hundreds):
        s = self._format_string(number % 10000, 'thousand_format', lang)
        return s.format(x_in_x00=number_tuple.x_in_x00,
                        xx00=number_tuple.xx00,
                        xx_in_xx00=number_tuple.xx_in_xx00,
                        x000=number_tuple.x000,
                        x_in_x000=number_tuple.x_in_x000,
                        x0_in_x000=number_tuple.x0_in_x000,
                        x_in_0x00=number_tuple.x_in_0x00,
                        formatted_decade=formatted_decade,
                        formatted_hundreds=formatted_hundreds,
                        number=str(number % 10000))

    def date_format(self, dt, lang, now):
        format_str = 'date_full'
        if now:
            if dt.year == now.year:
                format_str = 'date_full_no_year'
                if dt.month == now.month and dt.day > now.day:
                    format_str = 'date_full_no_year_month'

            tomorrow = now + datetime.timedelta(days=1)
            yesterday = now - datetime.timedelta(days=1)
            if tomorrow.date() == dt.date():
                format_str = 'tomorrow'
            elif now.date() == dt.date():
                format_str = 'today'
            elif yesterday.date() == dt.date():
                format_str = 'yesterday'

        return self.lang_config[lang]['date_format'][format_str].format(
            weekday=self.lang_config[lang]['weekday'][str(dt.weekday())],
            month=self.lang_config[lang]['month'][str(dt.month)],
            day=self.lang_config[lang]['date'][str(dt.day)],
            formatted_year=self.year_format(dt, lang, False))

    def date_time_format(self, dt, lang, now, use_24hour, use_ampm):
        date_str = self.date_format(dt, lang, now)
        time_str = nice_time(dt, lang, use_24hour=use_24hour,
                             use_ampm=use_ampm)
        return self.lang_config[lang]['date_time_format']['date_time'].format(
            formatted_date=date_str, formatted_time=time_str)

    def year_format(self, dt, lang, bc):
        number_tuple = self._number_strings(dt.year, lang)
        formatted_bc = (
            self.lang_config[lang]['year_format']['bc'] if bc else '')
        formatted_decade = self._decade_format(
            dt.year, number_tuple, lang)
        formatted_hundreds = self._number_format_hundreds(
            dt.year, number_tuple, lang, formatted_decade)
        formatted_thousand = self._number_format_thousand(
            dt.year, number_tuple, lang, formatted_decade, formatted_hundreds)

        s = self._format_string(dt.year, 'year_format', lang)

        return re.sub(' +', ' ',
                      s.format(
                          year=str(dt.year),
                          century=str(int(dt.year / 100)),
                          decade=str(dt.year % 100),
                          formatted_hundreds=formatted_hundreds,
                          formatted_decade=formatted_decade,
                          formatted_thousand=formatted_thousand,
                          bc=formatted_bc)).strip()


date_time_format = DateTimeFormat(
    os.path.dirname(os.path.abspath(__file__)) + '/../res/text')


def nice_number(number, lang=None, speech=True, denominators=None):
    """Format a float to human readable functions

    This function formats a float to human understandable functions. Like
    4.5 becomes 4 and a half for speech and 4 1/2 for text
    Args:
        number (int or float): the float to format
        lang (str): code for the language to use
        speech (bool): format for speech (True) or display (False)
        denominators (iter of ints): denominators to use, default [1 .. 20]
    Returns:
        (str): The formatted string.
    """
    # Convert to spoken representation in appropriate language
    lang_code = get_primary_lang_code(lang)
    if lang_code == "en":
        return nice_number_en(number, speech, denominators)
    elif lang_code == "es":
        return nice_number_es(number, speech, denominators)
    elif lang_code == "pt":
        return nice_number_pt(number, speech, denominators)
    elif lang_code == "it":
        return nice_number_it(number, speech, denominators)
    elif lang_code == "fr":
        return nice_number_fr(number, speech, denominators)
    elif lang_code == "sv":
        return nice_number_sv(number, speech, denominators)
    elif lang_code == "de":
        return nice_number_de(number, speech, denominators)
    elif lang_code == "hu":
        return nice_number_hu(number, speech, denominators)
    elif lang_code == "nl":
        return nice_number_nl(number, speech, denominators)
    elif lang_code == "da":
        return nice_number_da(number, speech, denominators)
    elif lang_code == "sv":
        return nice_number_sv(number, speech, denominators)

    # Default to the raw number for unsupported languages,
    # hopefully the STT engine will pronounce understandably.
    return str(number)


def nice_time(dt, lang=None, speech=True, use_24hour=False,
              use_ampm=False):
    """
    Format a time to a comfortable human format

    For example, generate 'five thirty' for speech or '5:30' for
    text display.

    Args:
        dt (datetime): date to format (assumes already in local timezone)
        lang (str): code for the language to use
        speech (bool): format for speech (default/True) or display (False)
        use_24hour (bool): output in 24-hour/military or 12-hour format
        use_ampm (bool): include the am/pm for 12-hour format
    Returns:
        (str): The formatted time string
    """
    lang_code = get_primary_lang_code(lang)
    if lang_code == "en":
        return nice_time_en(dt, speech, use_24hour, use_ampm)
    elif lang_code == "es":
        return nice_time_es(dt, speech, use_24hour, use_ampm)
    elif lang_code == "it":
        return nice_time_it(dt, speech, use_24hour, use_ampm)
    elif lang_code == "fr":
        return nice_time_fr(dt, speech, use_24hour, use_ampm)
    elif lang_code == "de":
        return nice_time_de(dt, speech, use_24hour, use_ampm)
    elif lang_code == "hu":
        return nice_time_hu(dt, speech, use_24hour, use_ampm)
    elif lang_code == "nl":
        return nice_time_nl(dt, speech, use_24hour, use_ampm)
    elif lang_code == "da":
        return nice_time_da(dt, speech, use_24hour, use_ampm)
    elif lang_code == "pt":
        return nice_time_pt(dt, speech, use_24hour, use_ampm)
    elif lang_code == "sv":
        return nice_time_sv(dt, speech, use_24hour, use_ampm)

    # TODO: Other languages
    return str(dt)


def pronounce_number(number, lang=None, places=2, short_scale=True,
                     scientific=False):
    """
    Convert a number to it's spoken equivalent

    For example, '5' would be 'five'

    Args:
        number: the number to pronounce
        short_scale (bool) : use short (True) or long scale (False)
            https://en.wikipedia.org/wiki/Names_of_large_numbers
        scientific (bool) : convert and pronounce in scientific notation
    Returns:
        (str): The pronounced number
    """
    lang_code = get_primary_lang_code(lang)
    if lang_code == "en":
        return pronounce_number_en(number, places=places,
                                   short_scale=short_scale,
                                   scientific=scientific)
    elif lang_code == "it":
        return pronounce_number_it(number, places=places,
                                   short_scale=short_scale,
                                   scientific=scientific)
    elif lang_code == "es":
        return pronounce_number_es(number, places=places)
    elif lang_code == "fr":
        return pronounce_number_fr(number, places=places)
    elif lang_code == "de":
        return pronounce_number_de(number, places=places)
    elif lang_code == "hu":
        return pronounce_number_hu(number, places=places)
    elif lang_code == "nl":
        return pronounce_number_nl(number, places=places)
    elif lang_code == "da":
        return pronounce_number_da(number, places=places)
    elif lang_code == "pt":
        return pronounce_number_pt(number, places=places)
    elif lang_code == "sv":
        return pronounce_number_sv(number, places=places)

    # Default to just returning the numeric value
    return str(number)


def nice_date(dt, lang=None, now=None):
    """
    Format a datetime to a pronounceable date

    For example, generates 'tuesday, june the fifth, 2018'
    Args:
        dt (datetime): date to format (assumes already in local timezone)
        lang (string): the language to use, use Mycroft default language if not
            provided
        now (datetime): Current date. If provided, the returned date for speech
            will be shortened accordingly: No year is returned if now is in the
            same year as td, no month is returned if now is in the same month
            as td. If now and td is the same day, 'today' is returned.
    Returns:
        (str): The formatted date string
    """
    full_code = get_full_lang_code(lang)
    date_time_format.cache(full_code)

    return date_time_format.date_format(dt, full_code, now)


def nice_date_time(dt, lang=None, now=None, use_24hour=False,
                   use_ampm=False):
    """
        Format a datetime to a pronounceable date and time

        For example, generate 'tuesday, june the fifth, 2018 at five thirty'

        Args:
            dt (datetime): date to format (assumes already in local timezone)
            lang (string): the language to use, use Mycroft default language if
                not provided
            now (datetime): Current date. If provided, the returned date for
                speech will be shortened accordingly: No year is returned if
                now is in the same year as td, no month is returned if now is
                in the same month as td. If now and td is the same day, 'today'
                is returned.
            use_24hour (bool): output in 24-hour/military or 12-hour format
            use_ampm (bool): include the am/pm for 12-hour format
        Returns:
            (str): The formatted date time string
    """

    full_code = get_full_lang_code(lang)
    date_time_format.cache(full_code)

    return date_time_format.date_time_format(dt, full_code, now, use_24hour,
                                             use_ampm)


def nice_year(dt, lang=None, bc=False):
    """
        Format a datetime to a pronounceable year

        For example, generate 'nineteen-hundred and eighty-four' for year 1984

        Args:
            dt (datetime): date to format (assumes already in local timezone)
            lang (string): the language to use, use Mycroft default language if
            not provided
            bc (bool) pust B.C. after the year (python does not support dates
                B.C. in datetime)
        Returns:
            (str): The formatted year string
    """

    full_code = get_full_lang_code(lang)
    date_time_format.cache(full_code)

    return date_time_format.year_format(dt, full_code, bc)


def _duration_handler(time1, lang=None, speech=True, *, time2=None,
                      use_years=True, clock=False,
                      resolution=TimeResolution.SECONDS):
    """ Convert duration in seconds to a nice spoken timespan
        Used as a handler by nice_duration and nice_duration_dt

    Accepts:
        datetime.timedelta, or
        seconds (int/float), or
        2 x datetime.datetime

    Examples:
       time1 = 60  ->  "1:00" or "one minute"
       time1 = 163  ->  "2:43" or "two minutes forty three seconds"
       time1 = timedelta(seconds=120)  ->  "2:00" or "two minutes"

       time1 = datetime(2019, 3, 12),
       time2 = datetime(2019, 1, 1)  ->  "seventy days"

    Args:
        time1: int/float seconds, OR datetime.timedelta, OR datetime.datetime
        time2 (datetime, optional): subtracted from time1 if time1 is datetime
        lang (str, optional): a BCP-47 language code, None for default
        speech (bool, opt): format output for speech (True) or display (False)
        use_years (bool, opt): rtn years and days if True, total days if False
        clock (bool, opt): always format output like digital clock (see below)
        resolution (mycroft.util.format.TimeResolution, optional): lower bound

            mycroft.util.format.TimeResolution values:
                TimeResolution.YEARS
                TimeResolution.DAYS
                TimeResolution.HOURS
                TimeResolution.MINUTES
                TimeResolution.SECONDS
                TimeResolution.MILLISECONDS
            NOTE: nice_duration will not produce milliseconds
            unless that resolution is passed.

            NOTE: clock will produce digital clock-like output appropriate to
            resolution. Has no effect on resolutions DAYS or YEARS. Only
            applies to displayed output.

    Returns:
        str: timespan as a string
    """
    _leapdays = 0
    _input_resolution = resolution
    milliseconds = 0

    type1 = type(time1)

    if time2:
        type2 = type(time2)
        if type1 is not type2:
            raise Exception("nice_duration() can't combine data types: "
                            "{} and {}".format(type1, type2))
        elif type1 is datetime.datetime:
            duration = time1 - time2
            _leapdays = (abs(leapdays(time1.year, time2.year)))

            # when operating on datetimes, refuse resolutions that
            # would result in bunches of trailing zeroes
            if all([time1.second == 0, time2.second == 0,
                    resolution.value >= TimeResolution.SECONDS.value]):
                resolution = TimeResolution.MINUTES
            if all([time1.minute == 0, time2.minute == 0,
                    resolution.value == TimeResolution.MINUTES.value]):
                resolution = TimeResolution.HOURS
            if all([time1.hour == 0, time2.hour == 0,
                    resolution.value == TimeResolution.HOURS.value]):
                resolution = TimeResolution.DAYS

        else:
            _tmp = warnings.formatwarning
            warnings.formatwarning = lambda msg, * \
                args, **kwargs: "{}\n".format(msg)
            warning = ("WARN: mycroft.util.format.nice_duration_dt() can't "
                       "subtract " + str(type1) + ". Ignoring 2nd "
                       "argument '" + str(time2) + "'.")
            warnings.warn(warning)
            warnings.formatwarning = _tmp
            duration = time1
    else:
        duration = time1

    # Pull decimal portion of seconds, if present, to use for milliseconds
    if isinstance(duration, float):
        milliseconds = str(duration).split('.')[1]
        if speech:
            milliseconds = milliseconds[:2]
        else:
            milliseconds = milliseconds[:3]
        milliseconds = float("0." + milliseconds)

    # Cast duration to datetime.timedelta for human-friendliness
    if not isinstance(duration, datetime.timedelta):
        duration = datetime.timedelta(seconds=duration)

    days = duration.days
    if use_years:
        days -= _leapdays if days > 365 else 0
        years = days // 365
    else:
        years = 0
    days = days % 365 if years > 0 else days

    # We already stored milliseconds. Now we want the integer part.
    seconds = duration.seconds
    minutes = seconds // 60
    seconds %= 60
    hours = minutes // 60
    minutes %= 60

    if speech:
        out = ""
        if years > 0:
            out += pronounce_number(years, lang) + " "
            out += _translate_word("year" if years == 1 else "years", lang)

        if days > 0 and resolution.value > TimeResolution.YEARS.value:
            if out:
                out += " "
            out += pronounce_number(days, lang) + " "
            out += _translate_word("day" if days == 1 else "days", lang)

        if hours > 0 and resolution.value > TimeResolution.DAYS.value:
            if out:
                out += " "
            out += pronounce_number(hours, lang) + " "
            out += _translate_word("hour" if hours == 1 else "hours", lang)

        if minutes > 0 and resolution.value > TimeResolution.HOURS.value:
            if out:
                out += " "
            out += pronounce_number(minutes, lang) + " "
            out += _translate_word("minute" if minutes ==
                                   1 else "minutes", lang)

        if ((seconds > 0 and resolution.value >=
             TimeResolution.SECONDS.value) or
            (milliseconds > 0 and resolution.value ==
             TimeResolution.MILLISECONDS.value)):

            if resolution.value == TimeResolution.MILLISECONDS.value:
                seconds += milliseconds
            if out:
                out += " "
                # Throw "and" between minutes and seconds if duration < 1 hour
                if len(out.split()) > 3 or seconds < 1:
                    out += _translate_word("and", lang) + " "
            # speaking "zero point five seconds" is better than "point five"
            if seconds < 1:
                out += pronounce_number(0, lang)
            out += pronounce_number(seconds, lang) + " "
            out += _translate_word("second" if seconds ==
                                   1 else "seconds", lang)

    else:
        # M:SS, MM:SS, H:MM:SS, Dd H:MM:SS format

        _seconds_str = ("0" + str(seconds)) if seconds < 10 else str(seconds)

        out = ""
        if years > 0:
            out = str(years) + "y "
        if days > 0 and resolution.value > TimeResolution.YEARS.value:
            out += str(days) + "d "
        if (hours > 0 and resolution.value > TimeResolution.DAYS.value) or \
                (clock and resolution is TimeResolution.HOURS):
            out += str(hours)

        if resolution.value == TimeResolution.MINUTES.value and not clock:
            out += (("h " + str(minutes) + "m") if hours > 0
                    else str(minutes) + "m")
        elif (minutes > 0 and resolution.value > TimeResolution.HOURS.value) \
                or (clock and resolution.value >= TimeResolution.HOURS.value):
            if hours != 0 or (clock and resolution is TimeResolution.HOURS):
                out += ":"
                if minutes < 10:
                    out += "0"
            out += str(minutes) + ":"
            if (seconds > 0 and resolution.value >
                    TimeResolution.MINUTES.value) or clock:
                out += _seconds_str
            else:
                out += "00"
        # if we have seconds but no minutes...
        elif (seconds > 0 or clock) and resolution.value > \
                TimeResolution.MINUTES.value:
            # check if output ends in hours
            try:
                if str(hours) == out.split()[-1]:
                    out += ":"
            except IndexError:
                pass
            out += ("00:" if hours > 0 else "0:") + _seconds_str

        if (milliseconds > 0 or clock) and resolution.value \
                == TimeResolution.MILLISECONDS.value:
            _mill = str(milliseconds).split(".")[1]
            # right-pad milliseconds to three decimal places
            while len(_mill) < 3:
                _mill += "0"
            # make sure output < 1s still formats correctly
            if out == "":
                out = "0:00"
            else:
                if (str(hours) == out.split()[-1]) and ":" not in out:
                    out += ":00:00"
            # only append milliseconds to output that contains
            # minutes and/or seconds
            if ":" in out:
                out += "." + _mill

        # If this evaluates True, out currently ends in hours: "1d 12"
        if out and all([resolution.value >= TimeResolution.HOURS.value,
                        ":" not in out, out[-1] != "m", hours > 0]):
            # to "1d 12h"
            out += "h"
        out = out.strip()

    if not out:
        out = "zero " if speech else "0"
        if _input_resolution == TimeResolution.YEARS:
            out += "years" if speech else "y"
        elif _input_resolution == TimeResolution.DAYS:
            out += "days" if speech else "d"
        elif _input_resolution == TimeResolution.HOURS:
            out += "hours" if speech else "h"
        elif _input_resolution == TimeResolution.MINUTES:
            if speech:
                out = "under a minute" if seconds > 0 else "zero minutes"
            else:
                out = "0m"
        else:
            out = "zero seconds" if speech else "0:00"

    return out


def nice_duration(duration, lang=None, speech=True, use_years=True,
                  clock=False, resolution=TimeResolution.SECONDS):
    """ Convert duration in seconds to a nice spoken timespan

    Accepts:
        time, in seconds, or datetime.timedelta

    Examples:
       duration = 60  ->  "1:00" or "one minute"
       duration = 163  ->  "2:43" or "two minutes forty three seconds"
       duration = timedelta(seconds=120)  ->  "2:00" or "two minutes"

    Args:
        duration (int/float/datetime.timedelta)
        lang (str, optional): a BCP-47 language code, None for default
        speech (bool, opt): format output for speech (True) or display (False)
        use_years (bool, opt): rtn years and days if True, total days if False
        clock (bool, opt): always format output like digital clock (see below)
        resolution (mycroft.util.format.TimeResolution, optional): lower bound

            mycroft.util.format.TimeResolution values:
                TimeResolution.YEARS
                TimeResolution.DAYS
                TimeResolution.HOURS
                TimeResolution.MINUTES
                TimeResolution.SECONDS
                TimeResolution.MILLISECONDS
            NOTE: nice_duration will not produce milliseconds
            unless that resolution is passed.

            NOTE: clock will produce digital clock-like output appropriate to
            resolution. Has no effect on resolutions DAYS or YEARS. Only
            applies to displayed output.

    Returns:
        str: timespan as a string
    """
    return _duration_handler(duration, lang=lang, speech=speech,
                             use_years=use_years, resolution=resolution,
                             clock=clock)


def nice_duration_dt(date1, date2, lang=None, speech=True, use_years=True,
                     clock=False, resolution=TimeResolution.SECONDS):
    """ Convert duration between datetimes to a nice spoken timespan

    Accepts:
        2 x datetime.datetime

    Examples:
        date1 = datetime(2019, 3, 12),
        date2 = datetime(2019, 1, 1)  ->  "seventy days"

        date1 = datetime(2019, 12, 25, 20, 30),
        date2 = datetime(2019, 10, 31, 8, 00),
        speech = False  ->  "55d 12:30"

    Args:
        date1, date2 (datetime.datetime)
        lang (str, optional): a BCP-47 language code, None for default
        speech (bool, opt): format output for speech (True) or display (False)
        use_years (bool, opt): rtn years and days if True, total days if False
        clock (bool, opt): always format output like digital clock (see below)
        resolution (mycroft.util.format.TimeResolution, optional): lower bound

            mycroft.util.format.TimeResolution values:
                TimeResolution.YEARS
                TimeResolution.DAYS
                TimeResolution.HOURS
                TimeResolution.MINUTES
                TimeResolution.SECONDS

            NOTE: nice_duration_dt() cannot do TimeResolution.MILLISECONDS
            This will silently fall back on TimeResolution.SECONDS

            NOTE: clock will produce digital clock-like output appropriate to
            resolution. Has no effect on resolutions DAYS or YEARS. Only
            applies to displayed output.

    Returns:
        str: timespan as a string
    """
    try:
        big = max(date1, date2)
        small = min(date1, date2)
    except(TypeError):
        big = date1
        small = date2
    return _duration_handler(big, lang=lang, speech=speech, time2=small,
                             use_years=use_years, resolution=resolution,
                             clock=clock)


def join_list(items, connector, sep=None, lang=None):
    """ Join a list into a phrase using the given connector word

    Examples:
        join_list([1,2,3], "and") ->  "1, 2 and 3"
        join_list([1,2,3], "and", ";") ->  "1; 2 and 3"

    Args:
        items(array): items to be joined
        connector(str): connecting word (resource name), like "and" or "or"
        sep(str, optional): separator character, default = ","
    Returns:
        str: the connected list phrase
    """

    if not items:
        return ""
    if len(items) == 1:
        return str(items[0])

    if not sep:
        sep = ", "
    else:
        sep += " "
    return (sep.join(str(item) for item in items[:-1]) +
            " " + _translate_word(connector, lang) +
            " " + items[-1])


def expand_options(parentheses_line: str) -> list:
    """
    Convert 'test (a|b)' -> ['test a', 'test b']
    Args:
        parentheses_line: Input line to expand
    Returns:
        List of expanded possibilities
    """
    # 'a(this|that)b' -> [['a', 'this', 'b'], ['a', 'that', 'b']]
    options = expand_parentheses(re.split(r'([(|)])', parentheses_line))
    return [re.sub(r'\s+', ' ', ' '.join(i)).strip() for i in options]
