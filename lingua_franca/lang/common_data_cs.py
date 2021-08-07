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


#_ARTICLES_CS = {}


_NUM_STRING_CS = {
    0: 'nula',
    1: 'jedna',
    2: 'dva',
    3: 'tři',
    4: 'čtyři',
    5: 'pět',
    6: 'šest',
    7: 'sedm',
    8: 'osm',
    9: 'devět',
    10: 'deset',
    11: 'jedenáct',
    12: 'dvanáct',
    13: 'třináct',
    14: 'čtrnáct',
    15: 'patnáct',
    16: 'šestnáct',
    17: 'sedmnáct',
    18: 'osmnáct',
    19: 'devatenáct',
    20: 'dvacet',
    30: 'třicet',
    40: 'čtyřicet',
    50: 'padesát',
    60: 'šedesát',
    70: 'sedmdesát',
    80: 'osmdesát',
    90: 'devadesát'
}


_FRACTION_STRING_CS = {
    2: 'polovina',
    3: 'třetina',
    4: 'čtvrtina',
    5: 'pětina',
    6: 'šestina',
    7: 'sedmina',
    8: 'osmina',
    9: 'devítina',
    10: 'desetina',
    11: 'jedenáctina',
    12: 'dvanáctina',
    13: 'třináctina',
    14: 'čtrnáctina',
    15: 'patnáctina',
    16: 'šestnáctina',
    17: 'sedmnáctina',
    18: 'osmnáctina',
    19: 'devatenáctina',
    20: 'dvacetina',
    30: 'třicetina',
    40: 'čtyřicetina',
    50: 'padesátina',
    60: 'šedesátina',
    70: 'sedmdesátina',
    80: 'osmdesátina',
    90: 'devadesátina',
    1e2: 'setina',
    1e3: 'tisícina'
}


_LONG_SCALE_CS = OrderedDict([
    (100, 'sto'),
    (1000, 'tisíc'),
    (1000000, 'milion'),
    (1e9, "miliarda"),
    (1e12, "bilion"),
    (1e15, "biliarda"),
    (1e18, "trilion"),
    (1e21, "triliarda"),
    (1e24, "kvadrilion"),
    (1e27, "kvadriliarda"),
    (1e30, "kvintilion"),
    (1e33, "kvintiliarda"),
    (1e36, "sextilion"),
    (1e39, "sextiliarda"),
    (1e42, "septilion"),
    (1e45, "septiliarda"),
    (1e48, "oktilion"),
    (1e51, "oktiliarda"),
    (1e54, "nonilion"),
    (1e57, "noniliarda"),
    (1e60, "decilion"),
    (1e63, "deciliarda"),
    (1e120, "vigintilion"),
    (1e180, "trigintilion"),
    (1e303, "kvinkvagintiliarda"),
    (1e600, "centilion"),
    (1e603, "centiliarda")
])


_SHORT_SCALE_CS = OrderedDict([
    (100, 'sto'),
    (1000, 'tisíc'),
    (1000000, 'million'),
    (1e9, "billion"),
    (1e12, 'trillion'),
    (1e15, "quadrillion"),
    (1e18, "quintillion"),
    (1e21, "sextillion"),
    (1e24, "septillion"),
    (1e27, "octillion"),
    (1e30, "nonillion"),
    (1e33, "decillion"),
    (1e36, "undecillion"),
    (1e39, "duodecillion"),
    (1e42, "tredecillion"),
    (1e45, "quadrdecillion"),
    (1e48, "quindecillion"),
    (1e51, "sexdecillion"),
    (1e54, "septendecillion"),
    (1e57, "octodecillion"),
    (1e60, "novemdecillion"),
    (1e63, "vigintillion"),
    (1e66, "unvigintillion"),
    (1e69, "uuovigintillion"),
    (1e72, "tresvigintillion"),
    (1e75, "quattuorvigintillion"),
    (1e78, "quinquavigintillion"),
    (1e81, "qesvigintillion"),
    (1e84, "septemvigintillion"),
    (1e87, "octovigintillion"),
    (1e90, "novemvigintillion"),
    (1e93, "trigintillion"),
    (1e96, "untrigintillion"),
    (1e99, "duotrigintillion"),
    (1e102, "trestrigintillion"),
    (1e105, "quattuortrigintillion"),
    (1e108, "quinquatrigintillion"),
    (1e111, "sestrigintillion"),
    (1e114, "septentrigintillion"),
    (1e117, "octotrigintillion"),
    (1e120, "noventrigintillion"),
    (1e123, "quadragintillion"),
    (1e153, "quinquagintillion"),
    (1e183, "sexagintillion"),
    (1e213, "septuagintillion"),
    (1e243, "octogintillion"),
    (1e273, "nonagintillion"),
    (1e303, "centillion"),
    (1e306, "uncentillion"),
    (1e309, "duocentillion"),
    (1e312, "trescentillion"),
    (1e333, "decicentillion"),
    (1e336, "undecicentillion"),
    (1e363, "viginticentillion"),
    (1e366, "unviginticentillion"),
    (1e393, "trigintacentillion"),
    (1e423, "quadragintacentillion"),
    (1e453, "quinquagintacentillion"),
    (1e483, "sexagintacentillion"),
    (1e513, "septuagintacentillion"),
    (1e543, "ctogintacentillion"),
    (1e573, "nonagintacentillion"),
    (1e603, "ducentillion"),
    (1e903, "trecentillion"),
    (1e1203, "quadringentillion"),
    (1e1503, "quingentillion"),
    (1e1803, "sescentillion"),
    (1e2103, "septingentillion"),
    (1e2403, "octingentillion"),
    (1e2703, "nongentillion"),
    (1e3003, "millinillion")
])


_ORDINAL_BASE_CS = {
    1: 'první',
    2: 'druhý',
    3: 'třetí',
    4: 'čtvrtý',
    5: 'pátý',
    6: 'šestý',
    7: 'sedmý',
    8: 'osmý',
    9: 'devátý',
    10: 'desátý',
    11: 'jedenáctý',
    12: 'dvanáctý',
    13: 'třináctý',
    14: 'čtrnáctý',
    15: 'patnáctý',
    16: 'šestnáctý',
    17: 'sedmnáctý',
    18: 'osmnáctý',
    19: 'devatenáctý',
    20: 'dvacátý',
    30: 'třicátý',
    40: "čtyřicátý",
    50: "padesátý",
    60: "šedesátý",
    70: "sedmdesátý",
    80: "osmdesátý",
    90: "devadesátý",
    1e2: "stý",
    1e3: "tisící"
}


_SHORT_ORDINAL_CS = {
    1e6: "miliontý",
    1e9: "billiontý",
    1e12: "trilliontý",
    1e15: "quadrilliontý",
    1e18: "quintilliontý",
    1e21: "sextilliontý",
    1e24: "septilliontý",
    1e27: "oktiliontý",
    1e30: "nonilliontý",
    1e33: "decilliontý"
    # TODO > 1e-33
}
_SHORT_ORDINAL_CS.update(_ORDINAL_BASE_CS)


_LONG_ORDINAL_CS = {
    1e6: "miliontý",
    1e9: "miliardtý",
    1e12: "biliontý",
    1e15: "biliardtý",
    1e18: "triliontý",
    1e21: "triliardtý",
    1e24: "kvadriliontý",
    1e27: "kvadriliardtý",
    1e30: "kvintiliontý",
    1e33: "kvintiliardtý",
    1e36: "sextiliontý",
    1e39: "sextiliardtý",
    1e42: "septiliontý",
    1e45: "septiliardtý",
    1e48: "oktilion",
    1e51: "oktiliardtý",
    1e54: "noniliontý",
    1e57: "noniliardtý",
    1e60: "deciliontý"
    # TODO > 1e60
}
_LONG_ORDINAL_CS.update(_ORDINAL_BASE_CS)

# Months

_MONTHS_CONVERSION = {
    0: "january",
    1: "february",
    2: "march",
    3: "april",
    4: "may",
    5: "june",
    6: "july",
    7: "august",
    8: "september",
    9: "october",
    10: "november",
    11: "december"
}

_MONTHS_CZECH = ['leden', 'únor', 'březen', 'duben', 'květen', 'červen',
                 'červenec', 'srpen', 'září', 'říjen', 'listopad',
                 'prosinec']

# Time
_TIME_UNITS_CONVERSION = {
    'mikrosekund': 'microseconds',
    'milisekund': 'milliseconds',
    'sekundu': 'seconds',
    'sekundy': 'seconds',
    'sekund': 'seconds',
    'minutu': 'minutes',
    'minuty': 'minutes',
    'minut': 'minutes',
    'hodin': 'hours',
    'den': 'days',  # 1 day
    'dny': 'days',  # 2-4 days
    'dnů': 'days',  # 5+ days
    'dní': 'days',  # 5+ days - different inflection
    'dne': 'days',  # a half day
    'týden': 'weeks',
    'týdny': 'weeks',
    'týdnů': 'weeks'
}
