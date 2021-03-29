#
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
"""Time utils for getting and converting datetime objects for the Mycroft
system. This time is based on the setting in the Mycroft config and may or
may not match the system locale.
"""
from datetime import datetime
from dateutil.tz import gettz, tzlocal

# LF ais optional and should not be needed because of time utils
# only parse and format utils require LF

# NOTE: lingua_franca has some bad UTC assumptions in date conversions,
# for that reason we do not import from there in this case

try:
    import lingua_franca as LF
except ImportError:
    LF = None


# backwards compat import, recommend using get_default_tz instead
def default_timezone():
    """Get the default timezone

    Based on user location settings location.timezone.code or
    the default system value if no setting exists.

    Returns:
        (datetime.tzinfo): Definition of the default timezone
    """
    from mycroft.configuration.locale import get_default_tz
    return get_default_tz()


def now_utc():
    """Retrieve the current time in UTC

    Returns:
        (datetime): The current time in Universal Time, aka GMT
    """
    return datetime.utcnow().replace(tzinfo=gettz("UTC"))


def now_local(tz=None):
    """Retrieve the current time

    Args:
        tz (datetime.tzinfo, optional): Timezone, default to user's settings

    Returns:
        (datetime): The current time
    """
    tz = tz or default_timezone()
    return datetime.now(tz)


def to_utc(dt):
    """Convert a datetime with timezone info to a UTC datetime

    Args:
        dt (datetime): A datetime (presumably in some local zone)
    Returns:
        (datetime): time converted to UTC
    """
    tz = gettz("UTC")
    if not dt.tzinfo:
        dt = dt.replace(tzinfo=default_timezone())
    return dt.astimezone(tz)


def to_local(dt):
    """Convert a datetime to the user's local timezone

   Args:
       dt (datetime): A datetime (if no timezone, defaults to UTC)
   Returns:
       (datetime): time converted to the local timezone
   """
    tz = default_timezone()
    if not dt.tzinfo:
        dt = dt.replace(tzinfo=default_timezone())
    return dt.astimezone(tz)


def to_system(dt):
    """Convert a datetime to the system's local timezone

    Args:
        dt (datetime): A datetime (if no timezone, assumed to be UTC)
    Returns:
        (datetime): time converted to the operation system's timezone
    """
    tz = tzlocal()
    if not dt.tzinfo:
        dt = dt.replace(tzinfo=default_timezone())
    return dt.astimezone(tz)
