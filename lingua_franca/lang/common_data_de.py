_DE_NUMBERS = {
    'null': 0,
    'ein': 1,
    'eins': 1,
    'eine': 1,
    'einer': 1,
    'einem': 1,
    'einen': 1,
    'eines': 1,
    'zwei': 2,
    'drei': 3,
    'vier': 4,
    'fünf': 5,
    'sechs': 6,
    'sieben': 7,
    'acht': 8,
    'neun': 9,
    'zehn': 10,
    'elf': 11,
    'zwölf': 12,
    'dreizehn': 13,
    'vierzehn': 14,
    'fünfzehn': 15,
    'sechzehn': 16,
    'siebzehn': 17,
    'achtzehn': 18,
    'neunzehn': 19,
    'zwanzig': 20,
    'einundzwanzig': 21,
    'zweiundzwanzig': 22,
    'dreiundzwanzig': 23,
    'vierundzwanzig': 24,
    'fünfundzwanzig': 25,
    'sechsundzwanzig': 26,
    'siebenundzwanzig': 27,
    'achtundzwanzig': 28,
    'neunundzwanzig': 29,
    'dreißig': 30,
    'einunddreißig': 31,
    'vierzig': 40,
    'fünfzig': 50,
    'sechzig': 60,
    'siebzig': 70,
    'achtzig': 80,
    'neunzig': 90,
    'hundert': 100,
    'zweihundert': 200,
    'dreihundert': 300,
    'vierhundert': 400,
    'fünfhundert': 500,
    'sechshundert': 600,
    'siebenhundert': 700,
    'achthundert': 800,
    'neunhundert': 900,
    'tausend': 1000,
    'million': 1000000
}

_MONTHS_DE = ['januar', 'februar', 'märz', 'april', 'mai', 'juni',
              'juli', 'august', 'september', 'oktober', 'november',
              'dezember']

_NUM_STRING_DE = {
    0: 'null',
    1: 'ein',  # ein Viertel etc., nicht eins Viertel
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
    16: 'sechzehn',
    17: 'siebzehn',
    18: 'achtzehn',
    19: 'neunzehn',
    20: 'zwanzig',
    30: 'dreißig',
    40: 'vierzig',
    50: 'fünfzig',
    60: 'sechzig',
    70: 'siebzig',
    80: 'achtzig',
    90: 'neunzig',
    100: 'hundert'
}

# German uses "long scale" https://en.wikipedia.org/wiki/Long_and_short_scales
# Currently, numbers are limited to 1000000000000000000000000,
# but _NUM_POWERS_OF_TEN can be extended to include additional number words


_NUM_POWERS_OF_TEN_DE = [
    '', 'tausend', 'Million', 'Milliarde', 'Billion', 'Billiarde', 'Trillion',
    'Trilliarde'
]

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
    16: 'sechzehntel',
    17: 'siebzehntel',
    18: 'achtzehntel',
    19: 'neunzehntel',
    20: 'zwanzigstel'
}

# Numbers below 1 million are written in one word in German, yielding very
# long words
# In some circumstances it may better to seperate individual words
# Set _EXTRA_SPACE_DA=" " for separating numbers below 1 million (
# orthographically incorrect)
# Set _EXTRA_SPACE_DA="" for correct spelling, this is standard

# _EXTRA_SPACE_DA = " "
_EXTRA_SPACE_DE = ""
