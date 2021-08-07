_FUNCTION_NOT_IMPLEMENTED_WARNING = "aquesta funció encara no s'ha implementat en 'ca'"

# Undefined articles ["un", "una", "uns", "unes"] can not be supressed,
# in CA, "un cavall" means "a horse" or "one horse".

_ARTICLES_CA = ["el", "la", "l", "lo", "els", "les", "los"]

# word rules for gender
_FEMALE_ENDINGS_CA = ["a", "esa", "essa", "esses", "eses", "ena", "enes",
                      "ques", "asi", "esi", "isi", "osi", "ut", "at",
                      "eta", "etes", "tja", "tges", "ica", "iques",
                      "ada", "ades"]
_MALE_ENDINGS_CA = ["o", "os", "ll", "lls", "ig", "igs", "itjos", "rs",
                    "et", "ets", "ès", "ns", "ic", "ics", "at", "ats"]

# special cases, word lookup for words not covered by above rule
_GENDERS_CA = {
    "dones": "f",
    "home": "m",
    "pell": "f",
    "pells": "f"
}

# context rules for gender
_MALE_DETERMINANTS_CA = ["el", "els", "l", "lo", "es", "aquest", "aquests",
                         "aquell", "aquells", "aqueix", "aqueixos",
                         "algun", "alguns", "este", "estos", "altre",
                         "mon", "mos", "mons", "meus", "meus"]
_FEMALE_DETERMINANTS_CA = ["la", "les", "sa", "ses", "aquesta", "aquestes",
                           "aquella", "aquelles", "aqueixa", "aqueixes",
                           "alguna", "algunes", "esta", "estes", "altra",
                           "ma", "mes", "meva", "meua", "meves"]

_NUMBERS_CA = {
    "zero": 0,
    "u": 1,
    "un": 1,
    "una": 1,
    "uns": 1,
    "unes": 1,
    "primer": 1,
    "primera": 1,
    "segon": 2,
    "segona": 2,
    "tercer": 3,
    "tercera": 3,
    "dos": 2,
    "dues": 2,
    "tres": 3,
    "quatre": 4,
    "cinc": 5,
    "sis": 6,
    "set": 7,
    "vuit": 8,
    "huit": 8,
    "nou": 9,
    "deu": 10,
    "onze": 11,
    "dotze": 12,
    "tretze": 13,
    "catorze": 14,
    "quinze": 15,
    "setze": 16,
    "disset": 17,
    "divuit": 18,
    "dinou": 19,
    "vint": 20,
    "trenta": 30,
    "quaranta": 40,
    "cinquanta": 50,
    "seixanta": 60,
    "setanta": 70,
    "vuitanta": 80,
    "noranta": 90,
    "cent": 100,
    "cents": 100,
    "dos-cents": 200,
    "dues-centes": 200,
    "tres-cents": 300,
    "tres-centes": 300,
    "quatre-cents": 400,
    "quatre-centes": 400,
    "cinc-cents": 500,
    "cinc-centes": 500,
    "sis-cents": 600,
    "sis-centes": 600,
    "set--cents": 700,
    "set-centes": 700,
    "vuit-cents": 800,
    "vuit-centes": 800,
    "nou-cents": 900,
    "nou-centes": 900,
    "mil": 1000,
    "milió": 1000000
}

_FRACTION_STRING_CA = {
    2: 'mig',
    3: 'terç',
    4: 'quart',
    5: 'cinquè',
    6: 'sisè',
    7: 'setè',
    8: 'vuitè',
    9: 'novè',
    10: 'desè',
    11: 'onzè',
    12: 'dotzè',
    13: 'tretzè',
    14: 'catorzè',
    15: 'quinzè',
    16: 'setzè',
    17: 'dissetè',
    18: 'divuitè',
    19: 'dinovè',
    20: 'vintè',
    30: 'trentè',
    100: 'centè',
    1000: 'milè'
}

_NUM_STRING_CA = {
    0: 'zero',
    1: 'un',
    2: 'dos',
    3: 'tres',
    4: 'quatre',
    5: 'cinc',
    6: 'sis',
    7: 'set',
    8: 'vuit',
    9: 'nou',
    10: 'deu',
    11: 'onze',
    12: 'dotze',
    13: 'tretze',
    14: 'catorze',
    15: 'quinze',
    16: 'setze',
    17: 'disset',
    18: 'divuit',
    19: 'dinou',
    20: 'vint',
    30: 'trenta',
    40: 'quaranta',
    50: 'cinquanta',
    60: 'seixanta',
    70: 'setanta',
    80: 'vuitanta',
    90: 'noranta'
}

_TENS_CA = {
    "vint": 20,
    "trenta": 30,
    "quaranta": 40,
    "cinquanta": 50,
    "seixanta": 60,
    "setanta": 70,
    "vuitanta": 80,
    "huitanta": 80,
    "noranta": 90
}

_AFTER_TENS_CA = {
    "u": 1,
    "un": 1,
    "dos": 2,
    "dues": 2,
    "tres": 3,
    "quatre": 4,
    "cinc": 5,
    "sis": 6,
    "set": 7,
    "vuit": 8,
    "huit": 8,
    "nou": 9
}

_BEFORE_HUNDREDS_CA = {
    "dos": 2,
    "dues": 2,
    "tres": 3,
    "quatre": 4,
    "cinc": 5,
    "sis": 6,
    "set": 7,
    "vuit": 8,
    "huit": 8,
    "nou": 9,
}

_HUNDREDS_CA = {
    "cent": 100,
    "cents": 100,
    "centes": 100
}
