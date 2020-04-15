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

The module uses lingua-franca (https://github.com/mycroftai/lingua-franca) to
do most of the actual parsing.

The focus of these formatting functions is to create natural sounding speech
and allow localization.
"""
import datetime
import warnings

from calendar import leapdays
from enum import Enum

import lingua_franca.format
# These are the main functions we are using lingua franca to provide
from lingua_franca.format import (NUMBER_TUPLE, DateTimeFormat, join_list,
                                  date_time_format, expand_options,
                                  _translate_word)

from padatious.util import expand_parentheses


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
    return lingua_franca.format.nice_number(number, lang, speech,
                                            denominators)


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
    return lingua_franca.format.nice_time(dt, lang, speech,
                                          use_24hour, use_ampm)


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
    return lingua_franca.format.pronounce_number(number, lang, places,
                                                 short_scale, scientific)


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
    return lingua_franca.format.nice_date(dt, lang, now)


def nice_date_time(dt, lang=None, now=None, use_24hour=False,
                   use_ampm=False):
    """Format a datetime to a pronounceable date and time.

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
    return lingua_franca.format.nice_date_time(dt, lang, now,
                                               use_24hour, use_ampm)


def nice_year(dt, lang=None, bc=False):
    """Format a datetime to a pronounceable year.

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
    return lingua_franca.format.nice_year(dt, lang, bc)


class TimeResolution(Enum):
    YEARS = 1
    DAYS = 2
    HOURS = 3
    MINUTES = 4
    SECONDS = 5
    MILLISECONDS = 6


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
