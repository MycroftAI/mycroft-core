# -*- coding: utf-8 -*-
#
# Copyright 2019 Mycroft AI Inc.
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

_ARTICLES_NL = {'de', 'het'}

_NUM_STRING_NL = {
    0: 'nul',
    1: 'een',
    2: 'twee',
    3: 'drie',
    4: 'vier',
    5: 'vijf',
    6: 'zes',
    7: 'zeven',
    8: 'acht',
    9: 'negen',
    10: 'tien',
    11: 'elf',
    12: 'twaalf',
    13: 'dertien',
    14: 'veertien',
    15: 'vijftien',
    16: 'zestien',
    17: 'zeventien',
    18: 'achttien',
    19: 'negentien',
    20: 'twintig',
    30: 'dertig',
    40: 'veertig',
    50: 'vijftig',
    60: 'zestig',
    70: 'zeventig',
    80: 'tachtig',
    90: 'negentig'
}

_FRACTION_STRING_NL = {
    2: 'half',
    3: 'derde',
    4: 'vierde',
    5: 'vijfde',
    6: 'zesde',
    7: 'zevende',
    8: 'achtste',
    9: 'negende',
    10: 'tiende',
    11: 'elfde',
    12: 'twaalfde',
    13: 'dertiende',
    14: 'veertiende',
    15: 'vijftiende',
    16: 'zestiende',
    17: 'zeventiende',
    18: 'achttiende',
    19: 'negentiende',
    20: 'twintigste'
}

_LONG_SCALE_NL = OrderedDict([
    (100, 'honderd'),
    (1000, 'duizend'),
    (1000000, 'miljoen'),
    (1e12, "biljoen"),
    (1e18, 'triljoen'),
    (1e24, "quadriljoen"),
    (1e30, "quintillion"),
    (1e36, "sextillion"),
    (1e42, "septillion"),
    (1e48, "octillion"),
    (1e54, "nonillion"),
    (1e60, "decillion"),
    (1e66, "undecillion"),
    (1e72, "duodecillion"),
    (1e78, "tredecillion"),
    (1e84, "quattuordecillion"),
    (1e90, "quinquadecillion"),
    (1e96, "sedecillion"),
    (1e102, "septendecillion"),
    (1e108, "octodecillion"),
    (1e114, "novendecillion"),
    (1e120, "vigintillion"),
    (1e306, "unquinquagintillion"),
    (1e312, "duoquinquagintillion"),
    (1e336, "sesquinquagintillion"),
    (1e366, "unsexagintillion")
])

_SHORT_SCALE_NL = OrderedDict([
    (100, 'honderd'),
    (1000, 'duizend'),
    (1000000, 'miljoen'),
    (1e9, "miljard"),
    (1e12, 'biljoen'),
    (1e15, "quadrillion"),
    (1e18, "quintiljoen"),
    (1e21, "sextiljoen"),
    (1e24, "septiljoen"),
    (1e27, "octiljoen"),
    (1e30, "noniljoen"),
    (1e33, "deciljoen"),
    (1e36, "undeciljoen"),
    (1e39, "duodeciljoen"),
    (1e42, "tredeciljoen"),
    (1e45, "quattuordeciljoen"),
    (1e48, "quinquadeciljoen"),
    (1e51, "sedeciljoen"),
    (1e54, "septendeciljoen"),
    (1e57, "octodeciljoen"),
    (1e60, "novendeciljoen"),
    (1e63, "vigintiljoen"),
    (1e66, "unvigintiljoen"),
    (1e69, "uuovigintiljoen"),
    (1e72, "tresvigintiljoen"),
    (1e75, "quattuorvigintiljoen"),
    (1e78, "quinquavigintiljoen"),
    (1e81, "qesvigintiljoen"),
    (1e84, "septemvigintiljoen"),
    (1e87, "octovigintiljoen"),
    (1e90, "novemvigintiljoen"),
    (1e93, "trigintiljoen"),
    (1e96, "untrigintiljoen"),
    (1e99, "duotrigintiljoen"),
    (1e102, "trestrigintiljoen"),
    (1e105, "quattuortrigintiljoen"),
    (1e108, "quinquatrigintiljoen"),
    (1e111, "sestrigintiljoen"),
    (1e114, "septentrigintiljoen"),
    (1e117, "octotrigintiljoen"),
    (1e120, "noventrigintiljoen"),
    (1e123, "quadragintiljoen"),
    (1e153, "quinquagintiljoen"),
    (1e183, "sexagintiljoen"),
    (1e213, "septuagintiljoen"),
    (1e243, "octogintiljoen"),
    (1e273, "nonagintiljoen"),
    (1e303, "centiljoen"),
    (1e306, "uncentiljoen"),
    (1e309, "duocentiljoen"),
    (1e312, "trescentiljoen"),
    (1e333, "decicentiljoen"),
    (1e336, "undecicentiljoen"),
    (1e363, "viginticentiljoen"),
    (1e366, "unviginticentiljoen"),
    (1e393, "trigintacentiljoen"),
    (1e423, "quadragintacentiljoen"),
    (1e453, "quinquagintacentiljoen"),
    (1e483, "sexagintacentiljoen"),
    (1e513, "septuagintacentiljoen"),
    (1e543, "ctogintacentiljoen"),
    (1e573, "nonagintacentiljoen"),
    (1e603, "ducentiljoen"),
    (1e903, "trecentiljoen"),
    (1e1203, "quadringentiljoen"),
    (1e1503, "quingentiljoen"),
    (1e1803, "sescentiljoen"),
    (1e2103, "septingentiljoen"),
    (1e2403, "octingentiljoen"),
    (1e2703, "nongentiljoen"),
    (1e3003, "milliniljoen")
])

_ORDINAL_STRING_BASE_NL = {
    1: 'eerste',
    2: 'tweede',
    3: 'derde',
    4: 'vierde',
    5: 'vijfde',
    6: 'zesde',
    7: 'zevende',
    8: 'achtste',
    9: 'negende',
    10: 'tiende',
    11: 'elfde',
    12: 'twaalfde',
    13: 'dertiende',
    14: 'veertiende',
    15: 'vijftiende',
    16: 'zestiende',
    17: 'zeventiende',
    18: 'achttiende',
    19: 'negentiende',
    20: 'twintigste',
    30: 'dertigste',
    40: "veertigste",
    50: "vijftigste",
    60: "zestigste",
    70: "zeventigste",
    80: "tachtigste",
    90: "negentigste",
    10e3: "honderdste",
    1e3: "duizendste"
}

_SHORT_ORDINAL_STRING_NL = {
    1e6: "miloenste",
    1e9: "miljardste",
    1e12: "biljoenste",
    1e15: "biljardste",
    1e18: "triljoenste",
    1e21: "trijardste",
    1e24: "quadriljoenste",
    1e27: "quadriljardste",
    1e30: "quintiljoenste",
    1e33: "quintiljardste"
    # TODO > 1e-33
}
_SHORT_ORDINAL_STRING_NL.update(_ORDINAL_STRING_BASE_NL)

_LONG_ORDINAL_STRING_NL = {
    1e6: "miloenste",
    1e9: "miljardste",
    1e12: "biljoenste",
    1e15: "biljardste",
    1e18: "triljoenste",
    1e21: "trijardste",
    1e24: "quadriljoenste",
    1e27: "quadriljardste",
    1e30: "quintiljoenste",
    1e33: "quintiljardste"
    # TODO > 1e60
}
_LONG_ORDINAL_STRING_NL.update(_ORDINAL_STRING_BASE_NL)

# negate next number (-2 = 0 - 2)
_NEGATIVES_NL = {"min", "minus"}

# sum the next number (twenty two = 20 + 2)
_SUMS_NL = {'twintig', '20', 'dertig', '30', 'veertig', '40', 'vijftig', '50',
            'zestig', '60', 'zeventig', '70', 'techtig', '80', 'negentig',
            '90'}

_MULTIPLIES_LONG_SCALE_NL = set(_LONG_SCALE_NL.values())

_MULTIPLIES_SHORT_SCALE_NL = set(_SHORT_SCALE_NL.values())

# split sentence parse separately and sum ( 2 and a half = 2 + 0.5 )
_FRACTION_MARKER_NL = {"en"}

# decimal marker ( 1 point 5 = 1 + 0.5)
_DECIMAL_MARKER_NL = {"komma", "punt"}

_STRING_NUM_NL = invert_dict(_NUM_STRING_NL)
_STRING_NUM_NL.update({
    "half": 0.5,
    "driekwart": 0.75,
    "anderhalf": 1.5,
    "paar": 2
})

_STRING_SHORT_ORDINAL_NL = invert_dict(_SHORT_ORDINAL_STRING_NL)
_STRING_LONG_ORDINAL_NL = invert_dict(_LONG_ORDINAL_STRING_NL)

_MONTHS_NL = ['januari', 'februari', 'maart', 'april', 'mei', 'juni',
              'juli', 'augustus', 'september', 'oktober', 'november',
              'december']

_NUM_STRING_NL = {
    0: 'nul',
    1: 'één',
    2: 'twee',
    3: 'drie',
    4: 'vier',
    5: 'vijf',
    6: 'zes',
    7: 'zeven',
    8: 'acht',
    9: 'negen',
    10: 'tien',
    11: 'elf',
    12: 'twaalf',
    13: 'dertien',
    14: 'veertien',
    15: 'vijftien',
    16: 'zestien',
    17: 'zeventien',
    18: 'actien',
    19: 'negentien',
    20: 'twintig',
    30: 'dertig',
    40: 'veertig',
    50: 'vijftig',
    60: 'zestig',
    70: 'zeventig',
    80: 'tachtig',
    90: 'negentig',
    100: 'honderd'
}

# Dutch uses "long scale" https://en.wikipedia.org/wiki/Long_and_short_scales
# Currently, numbers are limited to 1000000000000000000000000,
# but _NUM_POWERS_OF_TEN can be extended to include additional number words


_NUM_POWERS_OF_TEN = [
    '', 'duizend', 'miljoen', 'miljard', 'biljoen', 'biljard', 'triljoen',
    'triljard'
]

# Numbers below 1 million are written in one word in dutch, yielding very
# long words
# In some circumstances it may better to seperate individual words
# Set _EXTRA_SPACE_NL=" " for separating numbers below 1 million (
# orthographically incorrect)
# Set _EXTRA_SPACE_NL="" for correct spelling, this is standard

# _EXTRA_SPACE_NL = " "
_EXTRA_SPACE_NL = ""
