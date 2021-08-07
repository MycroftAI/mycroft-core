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

_FUNCTION_NOT_IMPLEMENTED_WARNING = "The requested function is not implemented in English."

_ARTICLES_EN = {'a', 'an', 'the'}


_NUM_STRING_EN = {
    0: 'zero',
    1: 'one',
    2: 'two',
    3: 'three',
    4: 'four',
    5: 'five',
    6: 'six',
    7: 'seven',
    8: 'eight',
    9: 'nine',
    10: 'ten',
    11: 'eleven',
    12: 'twelve',
    13: 'thirteen',
    14: 'fourteen',
    15: 'fifteen',
    16: 'sixteen',
    17: 'seventeen',
    18: 'eighteen',
    19: 'nineteen',
    20: 'twenty',
    30: 'thirty',
    40: 'forty',
    50: 'fifty',
    60: 'sixty',
    70: 'seventy',
    80: 'eighty',
    90: 'ninety'
}


_FRACTION_STRING_EN = {
    2: 'half',
    3: 'third',
    4: 'forth',
    5: 'fifth',
    6: 'sixth',
    7: 'seventh',
    8: 'eigth',
    9: 'ninth',
    10: 'tenth',
    11: 'eleventh',
    12: 'twelveth',
    13: 'thirteenth',
    14: 'fourteenth',
    15: 'fifteenth',
    16: 'sixteenth',
    17: 'seventeenth',
    18: 'eighteenth',
    19: 'nineteenth',
    20: 'twentyith'
}


_LONG_SCALE_EN = OrderedDict([
    (100, 'hundred'),
    (1000, 'thousand'),
    (1000000, 'million'),
    (1e12, "billion"),
    (1e18, 'trillion'),
    (1e24, "quadrillion"),
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


_SHORT_SCALE_EN = OrderedDict([
    (100, 'hundred'),
    (1000, 'thousand'),
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


_ORDINAL_BASE_EN = {
    1: 'first',
    2: 'second',
    3: 'third',
    4: 'fourth',
    5: 'fifth',
    6: 'sixth',
    7: 'seventh',
    8: 'eighth',
    9: 'ninth',
    10: 'tenth',
    11: 'eleventh',
    12: 'twelfth',
    13: 'thirteenth',
    14: 'fourteenth',
    15: 'fifteenth',
    16: 'sixteenth',
    17: 'seventeenth',
    18: 'eighteenth',
    19: 'nineteenth',
    20: 'twentieth',
    30: 'thirtieth',
    40: "fortieth",
    50: "fiftieth",
    60: "sixtieth",
    70: "seventieth",
    80: "eightieth",
    90: "ninetieth",
    1e2: "hundredth",
    1e3: "thousandth"
}


_SHORT_ORDINAL_EN = {
    1e6: "millionth",
    1e9: "billionth",
    1e12: "trillionth",
    1e15: "quadrillionth",
    1e18: "quintillionth",
    1e21: "sextillionth",
    1e24: "septillionth",
    1e27: "octillionth",
    1e30: "nonillionth",
    1e33: "decillionth"
    # TODO > 1e-33
}
_SHORT_ORDINAL_EN.update(_ORDINAL_BASE_EN)


_LONG_ORDINAL_EN = {
    1e6: "millionth",
    1e12: "billionth",
    1e18: "trillionth",
    1e24: "quadrillionth",
    1e30: "quintillionth",
    1e36: "sextillionth",
    1e42: "septillionth",
    1e48: "octillionth",
    1e54: "nonillionth",
    1e60: "decillionth"
    # TODO > 1e60
}
_LONG_ORDINAL_EN.update(_ORDINAL_BASE_EN)


# negate next number (-2 = 0 - 2)
_NEGATIVES_EN = {"negative", "minus"}

# sum the next number (twenty two = 20 + 2)
_SUMS_EN = {'twenty', '20', 'thirty', '30', 'forty', '40', 'fifty', '50',
            'sixty', '60', 'seventy', '70', 'eighty', '80', 'ninety', '90'}


def _generate_plurals_en(originals):
    """
    Return a new set or dict containing the plural form of the original values,

    In English this means all with 's' appended to them.

    Args:
        originals set(str) or dict(str, any): values to pluralize

    Returns:
        set(str) or dict(str, any)

    """
    # TODO migrate to https://github.com/MycroftAI/lingua-franca/pull/36
    if isinstance(originals, dict):
        return {key + 's': value for key, value in originals.items()}
    return {value + "s" for value in originals}


_MULTIPLIES_LONG_SCALE_EN = set(_LONG_SCALE_EN.values()) | \
    _generate_plurals_en(_LONG_SCALE_EN.values())

_MULTIPLIES_SHORT_SCALE_EN = set(_SHORT_SCALE_EN.values()) | \
    _generate_plurals_en(_SHORT_SCALE_EN.values())

# split sentence parse separately and sum ( 2 and a half = 2 + 0.5 )
_FRACTION_MARKER_EN = {"and"}

# decimal marker ( 1 point 5 = 1 + 0.5)
_DECIMAL_MARKER_EN = {"point", "dot"}

_STRING_NUM_EN = invert_dict(_NUM_STRING_EN)
_STRING_NUM_EN.update(_generate_plurals_en(_STRING_NUM_EN))

_SPOKEN_EXTRA_NUM_EN = {
            "half": 0.5,
            "halves": 0.5,
            "couple": 2
        }
_STRING_SHORT_ORDINAL_EN = invert_dict(_SHORT_ORDINAL_EN)
_STRING_LONG_ORDINAL_EN = invert_dict(_LONG_ORDINAL_EN)
