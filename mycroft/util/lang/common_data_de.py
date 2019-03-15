# -*- coding: utf-8 -*-
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


_ARTICLES = {
    'der', 'die', 'das',
    'dem', 'den', 'des',
    'ein', 'eine', 'einer',
    'einem','einen', 'einer'
}


_NUM_STRING_DE = {
    0: 'null',
    1: 'eins',
    2: 'zwei',
    3: 'drei',
    4: 'vier',
    5: 'fünf',
    6: 'sechs',
    7: 'sieben',
    8: 'acht',
    9: 'neun',
    10: 'zehn',
    11: 'elf',
    12: 'zwölf',
    13: 'dreizehn',
    14: 'vierzehn',
    15: 'fünfzehn',
    16: 'sechszehn',
    17: 'siebzehn',
    18: 'achtzehn',
    19: 'neunzehn',
    20: 'zwanzig',
    30: 'dreißig',
    40: 'vierzig',
    50: 'fünfzig',
    60: 'sechszig',
    70: 'siebzig',
    80: 'achtzig',
    90: 'neunzig'
}


_FRACTION_STRING_DE = {
    2: 'halb',
    3: 'drittel',
    4: 'viertel',
    5: 'fünftel',
    6: 'sechstel',
    7: 'siebtel',
    8: 'achtel',
    9: 'neuntel',
    10: 'zehntel',
    11: 'elftel',
    12: 'zwölftel',
    13: 'dreizehntel',
    14: 'vierzehntel',
    15: 'fünfzehntel',
    16: 'sechszehntel',
    17: 'siebzehntel',
    18: 'achtzehntel',
    19: 'neunzehntel',
    20: 'zwanzigstel'
}


_LONG_SCALE_DE = OrderedDict([
    (100, 'hundert'),
    (1000, 'tausend'),
    (1000000, 'million'),
    (1e9, "milliarde"),
    (1e12, "billion"),
    (1e15, "billiarde"),
    (1e18, 'trillion'),
    (1e21, "trilliarde"),
    (1e24, "quadrillion"),
    (1e27, "quadrilliarde"),
    (1e30, "quintillion"),
    (1e33, "quintilliarde"),
    (1e36, "sextillion"),
    (1e39, "sextilliarde"),
    (1e42, "septillion"),
    (1e45, "septilliarde"),
    (1e48, "oktillion"),
    (1e51, "oktilliarde"),
    (1e54, "nonillion"),
    (1e59, "nonilliarde"),
    (1e60, "dezillion"),
    (1e63, "dezilliarde"),
    (1e66, "undezillion"),
    (1e69, "undezilliarde"),
    (1e72, "duodezillion"),
    (1e15, "duodezilliarde"),
    (1e78, "tredezillion"),
    (1e81, "tredizilliarde"),
    (1e84, "quattuordezillion"),
    (1e87, "quattuordezilliarde"),
    (1e90, "quindezillion"),
    (1e93, "quindezilliarden"),
    (1e96, "sedezillion"),
    (1e99, "sedezilliarde"),
    (1e102, "septendezillion"),
    (1e105, "septendezilliarden"),
    (1e108, "duodevigintillion"),
    (1e114, "undevigintillion"),
    (1e120, "vigintillion")
])


_SHORT_SCALE_DE = OrderedDict([
    (100, 'hundert'),
    (1000, 'tausend'),
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
    (1e45, "quattuordecillion"),
    (1e48, "quinquadecillion"),
    (1e51, "sedecillion"),
    (1e54, "septendecillion"),
    (1e57, "octodecillion"),
    (1e60, "novendecillion"),
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


_ORDINAL_STRING_BASE_DE = {
    1: 'erst',
    2: 'zweit',
    3: 'dritt',
    4: 'viert',
    5: 'fünft',
    6: 'sechst',
    7: 'siebt',
    8: 'acht',
    9: 'neunt',
    10: 'zehnt',
    11: 'elft',
    12: 'zwölft',
    13: 'dreizehnt',
    14: 'vierzehnt',
    15: 'fünfzehnt',
    16: 'sechszehnt',
    17: 'siebzehnt',
    18: 'achtzehnt',
    19: 'neunzehnt',
    20: 'zwanzigst',
    30: 'dreißigst',
    40: "vierzigst",
    50: "fünfzigst",
    60: "sechszigst",
    70: "siebzigst",
    80: "achtzigst",
    90: "neunzigst",
    100: "einhundertst",
    1000: "eintausendst"
}


_SHORT_ORDINAL_STRING_DE = {
    1e6: "millionst",
    1e9: "billionst",
    1e12: "trillionst",
    1e15: "quadrillionst",
    1e18: "quintillionst",
    1e21: "sextillionst",
    1e24: "septillionst",
    1e27: "octillionst",
    1e30: "nonillionst",
    1e33: "decillionst"
    # TODO > 1e-33
}
_SHORT_ORDINAL_STRING_DE.update(_ORDINAL_STRING_BASE_DE)


_LONG_ORDINAL_STRING_DE = {
    1e6: "millionst",
    1e9: "milliardenst",
    1e12: "billionst",
    1e18: "trillionst",
    1e24: "quadrillionst",
    1e30: "quintillionst",
    1e36: "sextillionst",
    1e42: "septillionst",
    1e48: "octillionst",
    1e54: "nonillionst",
    1e60: "decillionst"
    # TODO > 1e60
}
_LONG_ORDINAL_STRING_DE.update(_ORDINAL_STRING_BASE_DE)
