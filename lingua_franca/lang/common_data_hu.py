_MONTHS_HU = ['január', 'február', 'március', 'április', 'május', 'június',
              'július', 'augusztus', 'szeptember', 'október', 'november',
              'december']

_NUM_STRING_HU = {
    0: 'nulla',
    1: 'egy',
    2: 'kettő',
    3: 'három',
    4: 'négy',
    5: 'öt',
    6: 'hat',
    7: 'hét',
    8: 'nyolc',
    9: 'kilenc',
    10: 'tíz',
    11: 'tizenegy',
    12: 'tizenkettő',
    13: 'tizenhárom',
    14: 'tizennégy',
    15: 'tizenöt',
    16: 'tizenhat',
    17: 'tizenhét',
    18: 'tizennyolc',
    19: 'tizenkilenc',
    20: 'húsz',
    30: 'harminc',
    40: 'negyven',
    50: 'ötven',
    60: 'hatvan',
    70: 'hetven',
    80: 'nyolcvan',
    90: 'kilencven',
    100: 'száz'
}

# Hungarian uses "long scale"
#    https://en.wikipedia.org/wiki/Long_and_short_scales
# Currently, numbers are limited to 1000000000000000000000000,
# but _NUM_POWERS_OF_TEN can be extended to include additional number words

_NUM_POWERS_OF_TEN = [
    '', 'ezer', 'millió', 'milliárd', 'billió', 'billiárd', 'trillió',
    'trilliárd'
]

_FRACTION_STRING_HU = {
    2: 'fél',
    3: 'harmad',
    4: 'negyed',
    5: 'ötöd',
    6: 'hatod',
    7: 'heted',
    8: 'nyolcad',
    9: 'kilenced',
    10: 'tized',
    11: 'tizenegyed',
    12: 'tizenketted',
    13: 'tizenharmad',
    14: 'tizennegyed',
    15: 'tizenötöd',
    16: 'tizenhatod',
    17: 'tizenheted',
    18: 'tizennyolcad',
    19: 'tizenkilenced',
    20: 'huszad'
}

# Numbers below 2 thousand are written in one word in Hungarian
# Numbers above 2 thousand are separated by hyphens
# In some circumstances it may better to seperate individual words
# Set _EXTRA_SPACE_HU=" " for separating numbers below 2 thousand (
# orthographically incorrect)
# Set _EXTRA_SPACE_HU="" for correct spelling, this is standard

# _EXTRA_SPACE_HU = " "
_EXTRA_SPACE_HU = ""
