_FUNCTION_NOT_IMPLEMENTED_WARNING = "Denne funktion er ikke implementeret i 'dk'."

_DA_NUMBERS = {
    'nul': 0,
    'en': 1,
    'et': 1,
    'to': 2,
    'tre': 3,
    'fire': 4,
    'fem': 5,
    'seks': 6,
    'syv': 7,
    'otte': 8,
    'ni': 9,
    'ti': 10,
    'elve': 11,
    'tolv': 12,
    'tretten': 13,
    'fjorten': 14,
    'femten': 15,
    'seksten': 16,
    'sytten': 17,
    'atten': 18,
    'nitten': 19,
    'tyve': 20,
    'enogtyve': 21,
    'toogtyve': 22,
    'treogtyve': 23,
    'fireogtyve': 24,
    'femogtyve': 25,
    'seksogtyve': 26,
    'syvogtyve': 27,
    'otteogtyve': 28,
    'niogtyve': 29,
    'tredive': 30,
    'enogtredive': 31,
    'fyrrre': 40,
    'halvtres': 50,
    'tres': 60,
    'halvfjers': 70,
    'firs': 80,
    'halvfems': 90,
    'hunderede': 100,
    'tohundrede': 200,
    'trehundrede': 300,
    'firehundrede': 400,
    'femhundrede': 500,
    'sekshundrede': 600,
    'syvhundrede': 700,
    'ottehundrede': 800,
    'nihundrede': 900,
    'tusinde': 1000,
    'million': 1000000
}

_MONTHS_DA = ['januar', 'februar', 'märz', 'april', 'mai', 'juni',
              'juli', 'august', 'september', 'oktober', 'november',
              'dezember']

_NUM_STRING_DA = {
    0: 'nul',
    1: 'en',
    2: 'to',
    3: 'tre',
    4: 'fire',
    5: 'fem',
    6: 'seks',
    7: 'syv',
    8: 'otte',
    9: 'ni',
    10: 'ti',
    11: 'elve',
    12: 'tolv',
    13: 'tretten',
    14: 'fjorten',
    15: 'femten',
    16: 'seksten',
    17: 'sytten',
    18: 'atten',
    19: 'nitten',
    20: 'tyve',
    30: 'tredive',
    40: 'fyrre',
    50: 'halvtres',
    60: 'tres',
    70: 'halvfjers',
    80: 'firs',
    90: 'halvfems',
    100: 'hundrede'
}

_NUM_POWERS_OF_TEN = [
    'hundred',
    'tusind',
    'million',
    'milliard',
    'billion',
    'billiard',
    'trillion',
    'trilliard'
]

_FRACTION_STRING_DA = {
    2: 'halv',
    3: 'trediedel',
    4: 'fjerdedel',
    5: 'femtedel',
    6: 'sjettedel',
    7: 'syvendedel',
    8: 'ottendedel',
    9: 'niendedel',
    10: 'tiendedel',
    11: 'elftedel',
    12: 'tolvtedel',
    13: 'trettendedel',
    14: 'fjortendedel',
    15: 'femtendedel',
    16: 'sejstendedel',
    17: 'syttendedel',
    18: 'attendedel',
    19: 'nittendedel',
    20: 'tyvendedel'
}

# Numbers below 1 million are written in one word in Danish, yielding very
# long words
# In some circumstances it may better to seperate individual words
# Set _EXTRA_SPACE_DA=" " for separating numbers below 1 million (
# orthographically incorrect)
# Set _EXTRA_SPACE_DA="" for correct spelling, this is standard

# _EXTRA_SPACE_DA = " "
_EXTRA_SPACE_DA = ""
