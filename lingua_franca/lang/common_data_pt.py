_FUNCTION_NOT_IMPLEMENTED_WARNING = "esta função não foi implementada em 'pt'"

# Undefined articles ["um", "uma", "uns", "umas"] can not be supressed,
# in PT, "um cavalo" means "a horse" or "one horse".

_ARTICLES_PT = ["o", "a", "os", "as"]

# word rules for gender
_FEMALE_ENDINGS_PT = ["a", "as"]
_MALE_ENDINGS_PT = ["o", "os"]

# special cases, word lookup for words not covered by above rule
_GENDERS_PT = {
    "mulher": "f",
    "mulheres": "f",
    "homem": "m"
}

# context rules for gender
_MALE_DETERMINANTS_PT = ["o", "os", "este", "estes", "esse", "esses"]
_FEMALE_DETERMINANTS_PT = ["a", "as", "estas", "estas", "essa", "essas"]

_NUMBERS_PT = {
    "zero": 0,
    "um": 1,
    "uma": 1,
    "uns": 1,
    "umas": 1,
    "primeiro": 1,
    "segundo": 2,
    "terceiro": 3,
    "dois": 2,
    "duas": 2,
    "tres": 3,
    "três": 3,
    "quatro": 4,
    "cinco": 5,
    "seis": 6,
    "sete": 7,
    "oito": 8,
    "nove": 9,
    "dez": 10,
    "onze": 11,
    "doze": 12,
    "treze": 13,
    "catorze": 14,
    "quinze": 15,
    "dezasseis": 16,
    "dezassete": 17,
    "dezoito": 18,
    "dezanove": 19,
    "vinte": 20,
    "trinta": 30,
    "quarenta": 40,
    "cinquenta": 50,
    "sessenta": 60,
    "setenta": 70,
    "oitenta": 80,
    "noventa": 90,
    "cem": 100,
    "cento": 100,
    "duzentos": 200,
    "duzentas": 200,
    "trezentos": 300,
    "trezentas": 300,
    "quatrocentos": 400,
    "quatrocentas": 400,
    "quinhentos": 500,
    "quinhentas": 500,
    "seiscentos": 600,
    "seiscentas": 600,
    "setecentos": 700,
    "setecentas": 700,
    "oitocentos": 800,
    "oitocentas": 800,
    "novecentos": 900,
    "novecentas": 900,
    "mil": 1000,
    "milhï¿½o": 1000000}

_FRACTION_STRING_PT = {
    2: 'meio',
    3: 'terço',
    4: 'quarto',
    5: 'quinto',
    6: 'sexto',
    7: 'sétimo',
    8: 'oitavo',
    9: 'nono',
    10: 'décimo',
    11: 'onze avos',
    12: 'doze avos',
    13: 'treze avos',
    14: 'catorze avos',
    15: 'quinze avos',
    16: 'dezasseis avos',
    17: 'dezassete avos',
    18: 'dezoito avos',
    19: 'dezanove avos',
    20: 'vigésimo',
    30: 'trigésimo',
    100: 'centésimo',
    1000: 'milésimo'
}

_NUM_STRING_PT = {
    0: 'zero',
    1: 'um',
    2: 'dois',
    3: 'três',
    4: 'quatro',
    5: 'cinco',
    6: 'seis',
    7: 'sete',
    8: 'oito',
    9: 'nove',
    10: 'dez',
    11: 'onze',
    12: 'doze',
    13: 'treze',
    14: 'catorze',
    15: 'quinze',
    16: 'dezasseis',
    17: 'dezassete',
    18: 'dezoito',
    19: 'dezanove',
    20: 'vinte',
    30: 'trinta',
    40: 'quarenta',
    50: 'cinquenta',
    60: 'sessenta',
    70: 'setenta',
    80: 'oitenta',
    90: 'noventa'
}
