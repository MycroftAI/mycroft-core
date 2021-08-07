#
# Copyright 2017 Mycroft AI Inc.
#
# Licensed under the Apache License, Version 2.0 (the 'License');
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an 'AS IS' BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
from collections import OrderedDict


_ARTICLES_SL = {}


_NUM_STRING_SL = {
    0: 'nič',
    1: 'ena',
    2: 'dve',
    3: 'tri',
    4: 'štiri',
    5: 'pet',
    6: 'šest',
    7: 'sedem',
    8: 'osem',
    9: 'devet',
    10: 'deset',
    11: 'enajst',
    12: 'dvanajst',
    13: 'trinajst',
    14: 'štirinajst',
    15: 'petnajst',
    16: 'šestnajst',
    17: 'sedemnajst',
    18: 'osemnajst',
    19: 'devetnajst',
    20: 'dvajset',
    30: 'trideset',
    40: 'štirideset',
    50: 'petdeset',
    60: 'šestdeset',
    70: 'sedemdeset',
    80: 'osemdeset',
    90: 'devetdeset'
}


_FRACTION_STRING_SL = {
    2: 'polovica',
    3: 'tretjina',
    4: 'četrtina',
    5: 'petina',
    6: 'šestina',
    7: 'sedmina',
    8: 'osmina',
    9: 'devetina',
    10: 'desetina',
    11: 'enajstina',
    12: 'dvanajstina',
    13: 'trinajstina',
    14: 'štirinajstina',
    15: 'petnajstina',
    16: 'šestnajstina',
    17: 'sedemnajstina',
    18: 'osemnajstina',
    19: 'devetnajstina',
    20: 'dvajsetina'
}


_LONG_SCALE_SL = OrderedDict([
    (100, 'sto'),
    (1000, 'tisoč'),
    (1000000, 'milijon'),
    (1e12, 'bilijon'),
    (1e18, 'trilijon'),
    (1e24, 'kvadrilijon'),
    (1e30, 'kvintilijon'),
    (1e36, 'sekstilijon'),
    (1e42, 'septilijon'),
    (1e48, 'oktilijon'),
    (1e54, 'nonilijon'),
    (1e60, 'decilijon')
    # TODO > 1e63
])


_SHORT_SCALE_SL = OrderedDict([
    (100, 'sto'),
    (1000, 'tisoč'),
    (1000000, 'milijon'),
    (1e9, 'bilijon'),
    (1e12, 'trilijon'),
    (1e15, 'kvadrilijon'),
    (1e18, 'kvintilijon'),
    (1e21, 'sekstilijon'),
    (1e24, 'septilijon'),
    (1e27, 'oktilijon'),
    (1e30, 'nonilijon'),
    (1e33, 'decilijon')
    # TODO > 1e33
])


_ORDINAL_BASE_SL = {
    1: 'prvi',
    2: 'drugi',
    3: 'tretji',
    4: 'četrti',
    5: 'peti',
    6: 'šesti',
    7: 'sedmi',
    8: 'osmi',
    9: 'deveti',
    10: 'deseti',
    11: 'enajsti',
    12: 'dvanajsti',
    13: 'trinajsti',
    14: 'štirinajsti',
    15: 'petnajsti',
    16: 'šestnajsti',
    17: 'sedemnajsti',
    18: 'osemnajsti',
    19: 'devetnajsti',
    20: 'dvajseti',
    30: 'trideseti',
    40: 'štirideseti',
    50: 'petdeseti',
    60: 'šestdeseti',
    70: 'sedemdeseti',
    80: 'osemdeseti',
    90: 'devetdeseti',
    1e2: 'stoti',
    1e3: 'tisoči'
}


_LONG_ORDINAL_SL = {
    1e6: 'milijonti',
    1e12: 'bilijonti',
    1e18: 'trilijonti',
    1e24: 'kvadrilijonti',
    1e30: 'kvintiljonti',
    1e36: 'sekstilijonti',
    1e42: 'septilijonti',
    1e48: 'oktilijonti',
    1e54: 'nonilijonti',
    1e60: 'decilijonti'
    # TODO > 1e60
}
_LONG_ORDINAL_SL.update(_ORDINAL_BASE_SL)


_SHORT_ORDINAL_SL = {
    1e6: 'milijonti',
    1e9: 'bilijonti',
    1e12: 'trilijonti',
    1e15: 'kvadrilijonti',
    1e18: 'kvintiljonti',
    1e21: 'sekstilijonti',
    1e24: 'septilijonti',
    1e27: 'oktilijonti',
    1e30: 'nonilijonti',
    1e33: 'decilijonti'
    # TODO > 1e33
}
_SHORT_ORDINAL_SL.update(_ORDINAL_BASE_SL)
