#
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
from collections import OrderedDict
from .parse_common import invert_dict

_FUNCTION_NOT_IMPLEMENTED_WARNING = "تابع خواسته شده در زبان فارسی پیاده سازی نشده است."


_FRACTION_STRING_FA = {
    2: 'دوم',
    3: 'سوم',
    4: 'چهارم',
    5: 'پنجم',
    6: 'ششم',
    7: 'هفتم',
    8: 'هشتم',
    9: 'نهم',
    10: 'دهم',
    11: 'یازدهم',
    12: 'دوازدهم',
    13: 'سیزدهم',
    14: 'چهاردهم',
    15: 'پونزدهم',
    16: 'شونزدهم',
    17: 'هیفدهم',
    18: 'هیجدهم',
    19: 'نوزدهم',
    20: 'بیستم'
}


_FARSI_ONES = [
    "",
    "یک",
    "دو",
    "سه",
    "چهار",
    "پنج",
    "شش",
    "هفت",
    "هشت",
    "نه",
    "ده",
    "یازده",
    "دوازده",
    "سیزده",
    "چهارده",
    "پونزده",
    "شونزده",
    "هیفده",
    "هیجده",
    "نوزده",
]

_FARSI_TENS = [
    "",
    "ده",
    "بیست",
    "سی",
    "چهل",
    "پنجاه",
    "شصت",
    "هفتاد",
    "هشتاد",
    "نود",
]

_FARSI_HUNDREDS = [
    "",
    "صد",
    "دویست",
    "سیصد",
    "چهارصد",
    "پانصد",
    "ششصد",
    "هفتصد",
    "هشتصد",
    "نهصد",
]

_FARSI_BIG = [
    '',
    'هزار',
    'میلیون',
    "میلیارد",
    'تریلیون',
    "تریلیارد",
]


_FORMAL_VARIANT = {
    'هفده': 'هیفده',
    'هجده': 'هیجده',
    'شانزده': 'شونزده',
    'پانزده': 'پونزده',
}


_FARSI_FRAC = ["", "ده", "صد"]
_FARSI_FRAC_BIG = ["", "هزار", "میلیونی", "میلیاردی"]

_FARSI_SEPERATOR = ' و '