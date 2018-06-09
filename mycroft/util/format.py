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

from mycroft.util.lang.format_en import *
from mycroft.util.lang.format_pt import *
from mycroft.util.lang.format_it import *
from mycroft.util.lang.format_sv import *

from mycroft.util.lang.format_fr import nice_number_fr
from mycroft.util.lang.format_fr import nice_time_fr
from mycroft.util.lang.format_fr import pronounce_number_fr

import json
import os
import datetime
import re


class DateTimeFormat:
    def __init__(self, config_path):
        self.lang_config = {}
        self.config_path = config_path

    def cache(self, lang):
        if lang not in self.lang_config:
            try:
                with open(self.config_path + '/' + lang + '/date_time.json',
                          'r') as lang_config_file:
                    self.lang_config[lang] = json.loads(
                        lang_config_file.read())
            except FileNotFoundError:
                with open(self.config_path + '/en-us/date_time.json',
                          'r') as lang_config_file:
                    self.lang_config[lang] = json.loads(
                        lang_config_file.read())

    def date_format(self, dt, lang, now):
        format_str = 'date_full'
        if now:
            if dt.year == now.year:
                format_str = 'date_full_no_year'
                if dt.month == now.month:
                    format_str = 'date_full_no_year_month'

            if (now + datetime.timedelta(1)).day == dt.day:
                format_str = 'tomorrow'
            if now.day == dt.day:
                format_str = 'today'
            if (now - datetime.timedelta(1)).day == dt.day:
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
        formatted_bc = (
            self.lang_config[lang]['year_format']['bc'] if bc else '')
        i = 1
        while self.lang_config[lang]['year_format'].get(str(i)):
            if (int(self.lang_config[lang]['year_format'][str(i)]['from']) <=
                    dt.year <=
                    int(self.lang_config[lang]['year_format'][str(i)]['to'])):
                return re.sub(' +', ' ',
                              self.lang_config[lang]['year_format'][str(i)][
                                  'format'].format(
                                  year=str(dt.year),
                                  century=str(int(dt.year / 100)),
                                  decade=str(dt.year % 100),
                                  bc=formatted_bc)).strip()
            i = i + 1

        return re.sub(' +', ' ',
                      self.lang_config[lang]['year_format']['default'].format(
                          year=str(dt.year),
                          century=str(int(dt.year / 100)),
                          decade=str(dt.year % 100),
                          bc=formatted_bc)).strip()


date_time_format = DateTimeFormat(
    os.path.dirname(os.path.abspath(__file__)) + '/../res/text')


def nice_number(number, lang="en-us", speech=True, denominators=None):
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
    lang_lower = str(lang).lower()
    if lang_lower.startswith("en"):
        return nice_number_en(number, speech, denominators)
    elif lang_lower.startswith("pt"):
        return nice_number_pt(number, speech, denominators)
    elif lang_lower.startswith("it"):
        return nice_number_it(number, speech, denominators)
    elif lang_lower.startswith("fr"):
        return nice_number_fr(number, speech, denominators)
    elif lang_lower.startswith("sv"):
        return nice_number_sv(number, speech, denominators)

    # Default to the raw number for unsupported languages,
    # hopefully the STT engine will pronounce understandably.
    return str(number)


def nice_time(dt, lang="en-us", speech=True, use_24hour=False,
              use_ampm=False):
    """
    Format a time to a comfortable human format

    For example, generate 'five thirty' for speech or '5:30' for
    text display.

    Args:
        dt (datetime): date to format (assumes already in local timezone)
        lang (str): code for the language to use
        speech (bool): format for speech (default/True) or display (False)=Fal
        use_24hour (bool): output in 24-hour/military or 12-hour format
        use_ampm (bool): include the am/pm for 12-hour format
    Returns:
        (str): The formatted time string
    """
    lang_lower = str(lang).lower()
    if lang_lower.startswith("en"):
        return nice_time_en(dt, speech, use_24hour, use_ampm)
    elif lang_lower.startswith("it"):
        return nice_time_it(dt, speech, use_24hour, use_ampm)
    elif lang_lower.startswith("fr"):
        return nice_time_fr(dt, speech, use_24hour, use_ampm)

    # TODO: Other languages
    return str(dt)


def pronounce_number(number, lang="en-us", places=2):
    """
    Convert a number to it's spoken equivalent

    For example, '5' would be 'five'

    Args:
        number: the number to pronounce
    Returns:
        (str): The pronounced number
    """
    lang_lower = str(lang).lower()
    if lang_lower.startswith("en"):
        return pronounce_number_en(number, places=places)
    elif lang_lower.startswith("it"):
        return pronounce_number_it(number, places=places)
    elif lang_lower.startswith("fr"):
        return pronounce_number_fr(number, places=places)

    # Default to just returning the numeric value
    return str(number)


def nice_date(dt, lang='en-us', now=None):
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

    date_time_format.cache(lang)

    return date_time_format.date_format(dt, lang, now)


def nice_date_time(dt, lang='en-us', now=None, use_24hour=False,
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

    date_time_format.cache(lang)

    return date_time_format.date_time_format(dt, lang, now, use_24hour,
                                             use_ampm)


def nice_year(dt, lang='en-us', bc=False):
    """
        Format a datetime to a pronounceable year

        For example, generate '20:18' that will be pronounced twenty eighteen

        Args:
            dt (datetime): date to format (assumes already in local timezone)
            lang (string): the language to use, use Mycroft default language if
            not provided
            bc (bool) pust B.C. after the year (python does not support dates
                B.C. in datetime)
        Returns:
            (str): The formatted year string
    """

    date_time_format.cache(lang)

    return date_time_format.year_format(dt, lang, bc)
