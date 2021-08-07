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
"""
    Parse functions for Italian (IT-IT)

"""

import collections
from datetime import datetime
from dateutil.relativedelta import relativedelta
from lingua_franca.lang.parse_common import is_numeric, look_for_fractions, \
    extract_numbers_generic, Normalizer
from lingua_franca.lang.format_it import _LONG_SCALE_IT, _SHORT_SCALE_IT, \
    pronounce_number_it
from lingua_franca.lang.common_data_it import _SHORT_ORDINAL_STRING_IT, \
    _ARTICLES_IT, _LONG_ORDINAL_STRING_IT, _STRING_NUM_IT


def is_fractional_it(input_str, short_scale=False):
    """
    This function takes the given text and checks if it is a fraction.
    Updated to italian from en version 18.8.9

    Args:
        input_str (str): the string to check if fractional
        short_scale (bool): use short scale if True, long scale if False
    Returns:
        (bool) or (float): False if not a fraction, otherwise the fraction

    """
    input_str = input_str.lower()
    if input_str.endswith('i', -1) and len(input_str) > 2:
        input_str = input_str[:-1] + "o"  # normalizza plurali

    fracts_it = {"intero": 1, "mezza": 2, "mezzo": 2}

    if short_scale:
        for num in _SHORT_ORDINAL_STRING_IT:
            if num > 2:
                fracts_it[_SHORT_ORDINAL_STRING_IT[num]] = num
    else:
        for num in _LONG_ORDINAL_STRING_IT:
            if num > 2:
                fracts_it[_LONG_ORDINAL_STRING_IT[num]] = num

    if input_str in fracts_it:
        return 1.0 / fracts_it[input_str]
    return False


def _extract_number_long_it(word):
    """
     This function converts a long textual number like
     milleventisette -> 1027 diecimila -> 10041 in
     integer value, covers from  0 to 999999999999999
     for now limited to 999_e21 but ready for 999_e63
     example:
        milleventisette -> 1027
        diecimilaquarantuno-> 10041
        centottomiladuecentotredici -> 108213
    Args:
         word (str): the word to convert in number
    Returns:
         (bool) or (int): The extracted number or False if no number
                                   was found
    """

    units = {'zero': 0, 'uno': 1, 'due': 2, 'tre': 3, 'quattro': 4,
             'cinque': 5, 'sei': 6, 'sette': 7, 'otto': 8, 'nove': 9}

    tens = {'dieci': 10, 'venti': 20, 'trenta': 30, 'quaranta': 40,
            'cinquanta': 50, 'sessanta': 60, 'settanta': 70, 'ottanta': 80,
            'novanta': 90}

    tens_short = {'vent': 20, 'trent': 30, 'quarant': 40, 'cinquant': 50,
                  'sessant': 60, 'settant': 70, 'ottant': 80, 'novant': 90}

    nums_long = {'undici': 11, 'dodici': 12, 'tredici': 13, 'quattordici': 14,
                 'quindici': 15, 'sedici': 16, 'diciassette': 17,
                 'diciotto': 18, 'diciannove': 19}

    multipli_it = collections.OrderedDict([
        # (1e63, 'deciliardi'),
        # (1e60, 'decilioni'),
        # (1e57, 'noviliardi'),
        # (1e54, 'novilioni'),
        # (1e51, 'ottiliardi'),
        # (1e48, 'ottilioni'),
        # (1e45, 'settiliardi'),
        # (1e42, 'settilioni'),
        # (1e39, 'sestiliardi'),
        # (1e36, 'sestilioni'),
        # (1e33, 'quintiliardi'),
        # (1e30, 'quintilioni'),
        # (1e27, 'quadriliardi'),
        # (1e24, 'quadrilioni'),    # yotta
        (1e21, 'triliardi'),  # zetta
        (1e18, 'trilioni'),  # exa
        (1e15, 'biliardi'),  # peta
        (1e12, 'bilioni'),  # tera
        (1e9, 'miliardi'),  # giga
        (1e6, 'milioni')  # mega
    ])

    multiplier = {}
    un_multiplier = {}

    for num in multipli_it:
        if num > 1000 and num <= 1e21:
            # plurali
            multiplier[multipli_it[num]] = int(num)
            # singolari - modificare per eccezioni *liardo
            if multipli_it[num][-5:-1] == 'iard':
                un_multiplier['un' + multipli_it[num][:-1] + 'o'] = int(num)
            else:
                un_multiplier['un' + multipli_it[num][:-1] + 'e'] = int(num)

    value = False

    # normalizza ordinali singoli o plurali -esimo -esimi
    if word[-5:-1] == 'esim':
        base = word[:-5]
        normalize_ita3 = {'tre': '', 'ttr': 'o', 'sei': '', 'ott': 'o'}
        normalize_ita2 = {'un': 'o', 'du': 'e', 'qu': 'e', 'tt': 'e',
                          'ov': 'e'}

        if base[-3:] in normalize_ita3:
            base += normalize_ita3[base[-3:]]
        elif base[-2:] in normalize_ita2:
            base += normalize_ita2[base[-2:]]

        word = base

    for item in un_multiplier:
        components = word.split(item, 1)
        if len(components) == 2:
            if not components[0]:  # inizia con un1^x
                if not components[1]:  # unmilione
                    word = str(int(un_multiplier[item]))
                else:  # unmilione + x
                    word = str(int(un_multiplier[item]) +
                               _extract_number_long_it(components[1]))

    for item in multiplier:
        components = word.split(item, 1)
        if len(components) == 2:
            if not components[0]:  # inizia con un1^x
                word = str(int(multiplier[item]) +
                           _extract_number_long_it(components[1]))
            else:
                if not components[1]:
                    word = str(_extract_number_long_it(components[0])) + '*' \
                        + str(int(multiplier[item]))
                else:
                    word = str(_extract_number_long_it(components[0])) + '*' \
                        + str(int(multiplier[item])) + '+' \
                        + str(_extract_number_long_it(components[1]))

    for item in tens:
        word = word.replace(item, '+' + str(tens[item]))

    for item in tens_short:
        word = word.replace(item, '+' + str(tens_short[item]))

    for item in nums_long:
        word = word.replace(item, '+' + str(nums_long[item]))

    word = word.replace('cento', '+1xx')
    word = word.replace('cent', '+1xx')
    word = word.replace('mille', '+1000')  # unmilionemille
    word = word.replace('mila', '*1000')  # unmilioneduemila

    for item in units:
        word = word.replace(item, '+' + str(units[item]))

    # normalizzo i cento
    occorrenze = word.count('+1xx')
    for _ in range(0, occorrenze):
        components = word.rsplit('+1xx', 1)
        if len(components[0]) > 1 and components[0].endswith('0'):
            word = components[0] + '+100' + components[1]
        else:
            word = components[0] + '*100' + components[1]

    components = word.rsplit('*1000', 1)
    if len(components) == 2:
        if components[0].startswith('*'):  # centomila
            components[0] = components[0][1:]
        word = str(_extract_number_long_it(components[0])) + \
            '*1000' + str(components[1])

    # gestione eccezioni
    if word.startswith('*') or word.startswith('+'):
        word = word[1:]

    addends = word.split('+')
    for c, _ in enumerate(addends):
        if '*' in addends[c]:
            factors = addends[c].split('*')
            result = int(factors[0]) * int(factors[1])
            if len(factors) == 3:
                result *= int(factors[2])
            addends[c] = str(result)

    # check if all token are numbers
    if all([s.isdecimal() for s in addends]):
        value = sum([int(s) for s in addends])
    else:
        value = False
    return value


def extract_number_it(text, short_scale=False, ordinals=False):
    """
    This function extracts a number from a text string,
    handles pronunciations in long scale and short scale

    https://en.wikipedia.org/wiki/Names_of_large_numbers

    Args:
        text (str): the string to normalize
        short_scale (bool): use short scale if True, long scale if False
        ordinals (bool): consider ordinal numbers, third=3 instead of 1/3
    Returns:
        (int) or (float) or False: The extracted number or False if no number
                                   was found

    """

    text = text.lower()
    string_num_ordinal_it = {}
    # first, second...
    if ordinals:
        if short_scale:
            for num in _SHORT_ORDINAL_STRING_IT:
                num_string = _SHORT_ORDINAL_STRING_IT[num]
                string_num_ordinal_it[num_string] = num
                _STRING_NUM_IT[num_string] = num
        else:
            for num in _LONG_ORDINAL_STRING_IT:
                num_string = _LONG_ORDINAL_STRING_IT[num]
                string_num_ordinal_it[num_string] = num
                _STRING_NUM_IT[num_string] = num

    # negate next number (-2 = 0 - 2)
    negatives = ['meno']  # 'negativo' non è usuale in italiano

    # multiply the previous number (one hundred = 1 * 100)
    multiplies = ['decina', 'decine', 'dozzina', 'dozzine',
                  'centinaia', 'centinaio', 'migliaia', 'migliaio', 'mila']

    # split sentence parse separately and sum ( 2 and a half = 2 + 0.5 )
    fraction_marker = [' e ']

    # decimal marker ( 1 point 5 = 1 + 0.5)
    decimal_marker = [' punto ', ' virgola ']

    if short_scale:
        for num in _SHORT_SCALE_IT:
            num_string = _SHORT_SCALE_IT[num]
            _STRING_NUM_IT[num_string] = num
            multiplies.append(num_string)
    else:
        for num in _LONG_SCALE_IT:
            num_string = _LONG_SCALE_IT[num]
            _STRING_NUM_IT[num_string] = num
            multiplies.append(num_string)

    # 2 e 3/4 ed altri casi
    for separator in fraction_marker:
        components = text.split(separator)
        zeros = 0

        if len(components) == 2:
            # count zeros in fraction part
            sub_components = components[1].split(' ')
            for element in sub_components:
                if element == 'zero' or element == '0':
                    zeros += 1
                else:
                    break
            # ensure first is not a fraction and second is a fraction
            num1 = extract_number_it(components[0])
            num2 = extract_number_it(components[1])
            if num1 is not None and num2 is not None \
                    and num1 >= 1 and 0 < num2 < 1:
                return num1 + num2
            # sette e quaranta  sette e zero zero due
            elif num1 is not None and num2 is not None \
                    and num1 >= 1 and num2 > 1:
                return num1 + num2 / pow(10, len(str(num2)) + zeros)

    # 2 punto 5
    for separator in decimal_marker:
        zeros = 0
        # count zeros in fraction part
        components = text.split(separator)

        if len(components) == 2:
            sub_components = components[1].split(' ')
            for element in sub_components:
                if element == 'zero' or element == '0':
                    zeros += 1
                else:
                    break

            number = int(extract_number_it(components[0]))
            decimal = int(extract_number_it(components[1]))
            if number is not None and decimal is not None:
                if '.' not in str(decimal):
                    return number + decimal / pow(10,
                                                  len(str(decimal)) + zeros)

    all_words = text.split()
    val = False
    prev_val = None
    to_sum = []
    for idx, word in enumerate(all_words):

        if not word:
            continue
        prev_word = all_words[idx - 1] if idx > 0 else ''
        next_word = all_words[idx + 1] if idx + 1 < len(all_words) else ''

        # is this word already a number ?
        if is_numeric(word):
            val = float(word)

        # is this word the name of a number ?
        if word in _STRING_NUM_IT:
            val = _STRING_NUM_IT[word]

        #  tre quarti  un quarto  trenta secondi
        if is_fractional_it(word) and prev_val:
            if word[:-1] == 'second' and not ordinals:
                val = prev_val * 2
            else:
                val = prev_val

        # is the prev word a number and should we multiply it?
        # twenty hundred, six hundred
        if word in multiplies:
            if not prev_val:
                prev_val = 1
            val = prev_val * val

        # is this a spoken fraction?
        # mezza tazza
        if val is False:
            val = is_fractional_it(word, short_scale=short_scale)

        # 2 quinti
        if not ordinals:
            next_value = is_fractional_it(next_word, short_scale=short_scale)
            if next_value:
                if not val:
                    val = 1
                val = val * next_value

        # is this a negative number?
        if val and prev_word and prev_word in negatives:
            val = 0 - val

        if not val:
            val = _extract_number_long_it(word)

        # let's make sure it isn't a fraction
        if not val:
            # look for fractions like '2/3'
            all_pieces = word.split('/')
            if look_for_fractions(all_pieces):
                val = float(all_pieces[0]) / float(all_pieces[1])
        else:
            prev_val = val
            # handle long numbers
            # six hundred sixty six
            # two million five hundred thousand
            if word in multiplies and next_word not in multiplies:
                to_sum.append(val)
                val = 0
                prev_val = 0
            elif _extract_number_long_it(word) > 100 and \
                    _extract_number_long_it(next_word) and \
                    next_word not in multiplies:
                to_sum.append(val)
                val = 0
                prev_val = 0

    if val is not None:
        for addend in to_sum:
            val = val + addend
    return val


def normalize_it(text, remove_articles=True):
    """ IT string normalization """
    # replace ambiguous words
    text = text.replace('un paio', 'due')

    words = text.split()  # this also removed extra spaces
    # Contractions are not common in IT
    # Convert numbers into digits, e.g. 'quarantadue' -> '42'
    normalized = ''
    i = 0

    while i < len(words):
        word = words[i]
        # remove articles
        # Italian requires the article to define the grammatical gender
        if remove_articles and word in _ARTICLES_IT:
            i += 1
            continue

        if word in _STRING_NUM_IT:
            word = str(_STRING_NUM_IT[word])

        val = int(extract_number_it(word))  # era extractnumber_long_it

        if val:
            word = str(val)

        normalized += ' ' + word
        i += 1
    # indefinite articles in it-it can not be removed

    return normalized[1:]


def extract_datetime_it(text, anchorDate=None, default_time=None):
    def clean_string(s):
        """
            cleans the input string of unneeded punctuation and capitalization
            among other things.
            Normalize italian plurals
        """
        symbols = ['.', ',', ';', '?', '!', 'º', 'ª', '°', 'l\'']

        for word in symbols:
            s = s.replace(word, '')

        s = s.lower().replace('á', 'a').replace('à', 'a').replace('è', "e'") \
            .replace('é', "e'").replace('ì', 'i').replace('ù', 'u') \
            .replace('ò', 'o').replace('-', ' ').replace('_', '')

        # normalizza plurali per semplificare analisi
        s = s.replace('secondi', 'secondo').replace('minuti', 'minuto') \
            .replace('ore', 'ora').replace('giorni', 'giorno') \
            .replace('settimane', 'settimana').replace('mesi', 'mese') \
            .replace('anni', 'anno').replace('mattino', 'mattina') \
            .replace('prossima', 'prossimo').replace('questa', 'questo') \
            .replace('quarti', 'quarto').replace('in punto', 'in_punto') \
            .replace('decennio', 'decenni').replace('secoli', 'secolo') \
            .replace('millennio', 'millenni').replace(' un ', ' uno ') \
            .replace('scorsa', 'scorso').replace('passata', 'passato') \
            .replace('uno paio', 'due')

        noise_words = ['dello', 'la', 'del', 'al', 'il', 'di', 'tra', 'lo',
                       'le', 'alle', 'alla', 'dai', 'delle', 'della',
                       'a', 'e\'', 'era', 'questa', 'questo', 'e', 'nel',
                       'nello', 'dallo', '  ']

        word_list = s.split()
        word_list = [x for x in word_list if x not in noise_words]
        # normalizza alcuni formati orari
        for idx in range(0, len(word_list) - 1):
            if word_list[idx][0].isdigit() and word_list[idx + 1][0].isdigit():
                num0 = int(word_list[idx])
                num1 = int(word_list[idx + 1])
                if 0 <= num0 <= 23 and 10 <= num1 <= 59:
                    word_list[idx] = str(num0) + ':' + str(num1)
                    word_list[idx + 1] = ''

        word_list = [x for x in word_list if x]

        return word_list

    def date_found():
        return found or \
            (datestr != '' or time_str != '' or year_offset != 0 or
                month_offset != 0 or day_offset is True or hr_offset != 0 or
                hr_abs or min_offset != 0 or min_abs or sec_offset != 0)

    if text == '' or not anchorDate:
        return None

    found = False
    day_specified = False
    day_offset = False
    month_offset = 0
    year_offset = 0
    today = anchorDate.strftime('%w')
    current_year = anchorDate.strftime('%Y')
    from_flag = False
    datestr = ''
    has_year = False
    time_qualifier = ''
    time_qualifiers_am = ['mattina', 'stamani', 'stamane']
    time_qualifiers_pm = ['pomeriggio', 'sera', 'stasera', 'stanotte']
    time_qualifiers_list = set(time_qualifiers_am + time_qualifiers_pm)
    markers = ['alle', 'in', 'questo', 'per', 'di', 'tra', 'fra', 'entro']
    days = ['lunedi', 'martedi', 'mercoledi',
            'giovedi', 'venerdi', 'sabato', 'domenica']
    months = ['gennaio', 'febbraio', 'marzo', 'aprile', 'maggio', 'giugno',
              'luglio', 'agosto', 'settembre', 'ottobre', 'novembre',
              'dicembre']
    months_short = ['gen', 'feb', 'mar', 'apr', 'mag', 'giu', 'lug', 'ago',
                    'set', 'ott', 'nov', 'dic']
    year_multiples = ['decenni', 'secolo', 'millenni']  # decennio <- decenni
    time_multiples = ['ora', 'minuto', 'secondo']
    day_multiples = ['settimana', 'mese', 'anno']
    noise_words_2 = ['tra', 'di', 'per', 'fra', 'un ', 'uno', 'lo', 'del',
                     'l', 'in_punto', ' ', 'nella', 'dell']

    words = clean_string(text)

    for idx, word in enumerate(words):
        if word == '':
            continue
        word_prev_prev = words[idx - 2] if idx > 1 else ''
        word_prev = words[idx - 1] if idx > 0 else ''
        word_next = words[idx + 1] if idx + 1 < len(words) else ''
        word_next_next = words[idx + 2] if idx + 2 < len(words) else ''
        start = idx
        used = 0
        # save timequalifier for later
        if word == 'adesso' and not datestr:
            # word == 'ora' va in conflitto con 'tra un ora'
            words = [x for x in words if x != 'adesso']
            words = [x for x in words if x]
            result_str = ' '.join(words)
            extracted_date = anchorDate.replace(microsecond=0)
            return [extracted_date, result_str]

        # un paio di  o  tra tre settimane --> secoli
        elif extract_number_it(word) and (word_next in year_multiples or
                                          word_next in day_multiples):
            multiplier = int(extract_number_it(word))
            used += 2
            if word_next == 'decenni':
                year_offset = multiplier * 10
            elif word_next == 'secolo':
                year_offset = multiplier * 100
            elif word_next == 'millenni':
                year_offset = multiplier * 1000
            elif word_next == 'anno':
                year_offset = multiplier
            elif word_next == 'mese':
                month_offset = multiplier
            elif word_next == 'settimana':
                day_offset = multiplier * 7
        elif word in time_qualifiers_list:
            time_qualifier = word
        # parse today, tomorrow, day after tomorrow
        elif word == 'oggi' and not from_flag:
            day_offset = 0
            used += 1
        elif word == 'domani' and not from_flag:
            day_offset = 1
            used += 1
        elif word == 'ieri' and not from_flag:
            day_offset -= 1
            used += 1
        elif word == 'dopodomani' and not from_flag:  # after tomorrow
            day_offset += 2
            used += 1
        elif word == 'dopo' and word_next == 'domani' and not from_flag:
            day_offset += 1
            used += 2
        elif word == 'giorno':
            if word_prev[0].isdigit():
                day_offset += int(word_prev)
                start -= 1
                used = 2
                if word_next == 'dopo' and word_next_next == 'domani':
                    day_offset += 1
                    used += 2
        elif word == 'settimana' and not from_flag:
            if word_prev == 'prossimo':
                day_offset = 7
                start -= 1
                used = 2
            elif word_prev == 'passato' or word_prev == 'scorso':
                day_offset = -7
                start -= 1
                used = 2
            elif word_next == 'prossimo':
                day_offset = 7
                used += 2
            elif word_next == 'passato' or word_next == 'scorso':
                day_offset = -7
                used += 2
        # parse next month, last month
        elif word == 'mese' and not from_flag:
            if word_prev == 'prossimo':
                month_offset = 1
                start -= 1
                used = 2
            elif word_prev == 'passato' or word_prev == 'scorso':
                month_offset = -1
                start -= 1
                used = 2
            elif word_next == 'prossimo':
                month_offset = 1
                used += 2
            elif word_next == 'passato' or word_next == 'scorso':
                month_offset = -1
                used += 2
        # parse next year, last year
        elif word == 'anno' and not from_flag:
            if word_prev == 'prossimo':  # prossimo anno
                year_offset = 1
                start -= 1
                used = 2
            elif word_next == 'prossimo':  # anno prossimo
                year_offset = 1
                used = 2
            elif word_prev == 'passato' or word_prev == 'scorso':
                year_offset = -1
                start -= 1
                used = 2
            elif word_next == 'passato' or word_next == 'scorso':
                year_offset = -1
                used = 2
        elif word == 'decenni' and not from_flag:
            if word_prev == 'prossimo':  # prossimo mese
                year_offset = 10
                start -= 1
                used = 2
            elif word_next == 'prossimo':  # mese prossimo
                year_offset = 10
                used = 2
            elif word_prev == 'passato' or word_prev == 'scorso':
                year_offset = -10
                start -= 1
                used = 2
            elif word_next == 'passato' or word_next == 'scorso':
                year_offset = -10
                used = 2
        # parse Monday, Tuesday, etc., and next Monday,
        # last Tuesday, etc.
        elif word in days and not from_flag:
            ddd = days.index(word)
            day_offset = (ddd + 1) - int(today)
            used = 1
            if day_offset < 0:
                day_offset += 7
            if word_prev == 'prossimo':
                day_offset += 7
                start -= 1
                used += 1
            elif word_prev == 'passato' or word_prev == 'scorso':
                day_offset -= 7
                start -= 1
                used += 1
            if word_next == 'prossimo':
                day_offset += 7
                used += 1
            elif word_next == 'passato' or word_next == 'scorso':
                day_offset -= 7
                used += 1
        # parse 15 of July, June 20th, Feb 18, 19 of February
        elif word in months or word in months_short and not from_flag:
            try:
                mmm = months.index(word)
            except ValueError:
                mmm = months_short.index(word)
            used += 1
            datestr = months[mmm]
            if word_prev and extract_number_it(word_prev):
                datestr += ' ' + str(int(extract_number_it(word_prev)))
                start -= 1
                used += 1
                if word_next and extract_number_it(word_next):
                    datestr += ' ' + str(int(extract_number_it(word_next)))
                    used += 1
                    has_year = True
                else:
                    has_year = False
            elif word_next and word_next[0].isdigit():
                datestr += ' ' + word_next
                used += 1
                if word_next_next and word_next_next[0].isdigit():
                    datestr += ' ' + word_next_next
                    used += 1
                    has_year = True
                else:
                    has_year = False
        # parse 5 days from tomorrow, 10 weeks from next thursday,
        # 2 months from July
        validFollowups = days + months + months_short
        validFollowups.append('oggi')
        validFollowups.append('domani')
        validFollowups.append('prossimo')
        validFollowups.append('passato')
        validFollowups.append('adesso')

        if (word == 'da' or word == 'dopo') and word_next in validFollowups:
            used = 0
            from_flag = True
            if word_next == 'domani':
                day_offset += 1
                used += 2
            elif word_next == 'oggi' or word_next == 'adesso':
                used += 2
            elif word_next in days:
                ddd = days.index(word_next)
                tmp_offset = (ddd + 1) - int(today)
                used += 2
                if tmp_offset < 0:
                    tmp_offset += 7
                if word_next_next == 'prossimo':
                    tmp_offset += 7
                    used += 1
                elif word_next_next == 'passato' or word_next_next == 'scorso':
                    tmp_offset = (ddd + 1) - int(today)
                    used += 1
                day_offset += tmp_offset
            elif word_next_next and word_next_next in days:
                ddd = days.index(word_next_next)
                tmp_offset = (ddd + 1) - int(today)
                if word_next == 'prossimo':
                    tmp_offset += 7
                # elif word_next == 'passato' or word_next == 'scorso':
                #    tmp_offset -= 7
                day_offset += tmp_offset
                used += 3

        if used > 0:
            if start - 1 > 0 and words[start - 1] == 'questo':
                start -= 1
                used += 1

            for i in range(0, used):
                words[i + start] = ''

            if start - 1 >= 0 and words[start - 1] in markers:
                words[start - 1] = ''
            found = True
            day_specified = True

    # parse time
    time_str = ''
    hr_offset = 0
    min_offset = 0
    sec_offset = 0
    hr_abs = None
    min_abs = None
    military = False

    for idx, word in enumerate(words):
        if word == '':
            continue
        word_prev_prev = words[idx - 2] if idx > 1 else ''
        word_prev = words[idx - 1] if idx > 0 else ''
        word_next = words[idx + 1] if idx + 1 < len(words) else ''
        word_next_next = words[idx + 2] if idx + 2 < len(words) else ''
        # parse noon, midnight, morning, afternoon, evening
        used = 0
        if word == 'mezzogiorno':
            hr_abs = 12
            used += 1
        elif word == 'mezzanotte':
            hr_abs = 24
            used += 1
        if word == 'mezzo' and word_next == 'giorno':
            hr_abs = 12
            used += 2
        elif word == 'mezza' and word_next == 'notte':
            hr_abs = 24
            used += 2
        elif word == 'mattina':
            if not hr_abs:
                hr_abs = 8
            used += 1
            if word_next and word_next[0].isdigit():  # mattina alle 5
                hr_abs = int(word_next)
                used += 1
        elif word == 'pomeriggio':
            if not hr_abs:
                hr_abs = 15
            used += 1
            if word_next and word_next[0].isdigit():  # pomeriggio alle 5
                hr_abs = int(word_next)
                used += 1
                if (hr_abs or 0) < 12:
                    hr_abs = (hr_abs or 0) + 12
        elif word == 'sera':
            if not hr_abs:
                hr_abs = 19
            used += 1
            if word_next and word_next[0].isdigit() \
                    and ':' not in word_next:
                hr_abs = int(word_next)
                used += 1
                if (hr_abs or 0) < 12:
                    hr_abs = (hr_abs or 0) + 12
        # da verificare più a fondo
        elif word == 'presto':
            hr_abs -= 1
            used += 1
        elif word == 'tardi':
            hr_abs += 1
            used += 1
        # un paio di minuti  tra cinque minuti tra 5 ore
        elif extract_number_it(word) and (word_next in time_multiples):
            d_time = int(extract_number_it(word))
            used += 2
            if word_next == 'ora':
                hr_offset = d_time
                isTime = False
                hr_abs = -1
                min_abs = -1
            elif word_next == 'minuto':
                min_offset = d_time
                isTime = False
                hr_abs = -1
                min_abs = -1
            elif word_next == 'secondo':
                sec_offset = d_time
                isTime = False
                hr_abs = -1
                min_abs = -1
        elif word == 'mezzora':
            min_offset = 30
            used = 1
            isTime = False
            hr_abs = -1
            min_abs = -1
            # if word_prev == 'uno' or word_prev == 'una':
            #    start -= 1
            #    used += 1
        elif extract_number_it(word) and word_next and \
                word_next == 'quarto' and word_next_next == 'ora':
            if int(extract_number_it(word)) == 1 \
                    or int(extract_number_it(word)) == 3:
                min_offset = 15 * int(extract_number_it(word))
            else:  # elimina eventuali errori
                min_offset = 15
            used = 3
            start -= 1
            isTime = False
            hr_abs = -1
            min_abs = -1
        elif word[0].isdigit():
            isTime = True
            str_hh = ''
            str_mm = ''
            remainder = ''
            if ':' in word:
                # parse colons
                # '3:00 in the morning'
                components = word.split(':')
                if len(components) == 2:
                    num0 = int(extract_number_it(components[0]))
                    num1 = int(extract_number_it(components[1]))
                    if num0 is not False and num1 is not False \
                            and 0 <= num0 <= 23 and 0 <= num1 <= 59:
                        str_hh = str(num0)
                        str_mm = str(num1)
            elif 0 < int(extract_number_it(word)) < 24 \
                    and word_next != 'quarto':
                str_hh = str(int(word))
                str_mm = '00'
            elif 100 <= int(word) <= 2400:
                str_hh = int(word) / 100
                str_mm = int(word) - str_hh * 100
                military = True
                isTime = False
            if extract_number_it(word) and word_next \
                    and word_next == 'quarto' and word_next_next != 'ora':
                if int(extract_number_it(word)) == 1 \
                        or int(extract_number_it(word)) == 3:
                    str_mm = str(15 * int(extract_number_it(word)))
                else:  # elimina eventuali errori
                    str_mm = '0'
                str_hh = str(hr_abs)
                used = 2
                words[idx + 1] = ''
                isTime = False
            if extract_number_it(word) and word_next \
                    and word_next == 'in_punto':
                str_hh = str(int(extract_number_it(word)))
                used = 2
            if word_next == 'pm':
                remainder = 'pm'
                hr_abs = int(str_hh)
                min_abs = int(str_mm)
                if hr_abs <= 12:
                    hr_abs = hr_abs + 12
                used = 2
            elif word_next == 'am':
                remainder = 'am'
                hr_abs = int(str_hh)
                min_abs = int(str_mm)
                used = 2
            elif word_next == 'mattina':
                # ' 11 del mattina'
                hh = int(str_hh)
                mm = int(str_mm)
                used = 2
                remainder = 'am'
                isTime = False
                hr_abs = hh
                min_abs = mm
            elif word_next == 'pomeriggio':
                # ' 2 del pomeriggio'
                hh = int(str_hh)
                mm = int(str_mm)
                if hh < 12:
                    hh += 12
                used = 2
                remainder = 'pm'
                isTime = False
                hr_abs = hh
                min_abs = mm
            elif word_next == 'sera':
                # 'alle 8 di sera'
                hh = int(str_hh)
                mm = int(str_mm)
                if hh < 12:
                    hh += 12
                used = 2
                remainder = 'pm'
                isTime = False
                hr_abs = hh
                min_abs = mm
            elif word_next == 'notte':
                hh = int(str_hh)
                mm = int(str_mm)
                if hh > 5:
                    remainder = 'pm'
                else:
                    remainder = 'am'
                used = 2
                isTime = False
                hr_abs = hh
                min_abs = mm
            # parse half an hour : undici e mezza
            elif word_next and word_next == 'mezza':
                hr_abs = int(str_hh)
                min_abs = 30
                used = 2
                isTime = False
            elif word_next and word_next == 'in_punto':
                hr_abs = int(str_hh)
                min_abs = 0
                str_mm = '0'
                used = 2
                isTime = False
            else:
                # 17:30
                remainder = ''
                hr_abs = int(str_hh)
                min_abs = int(str_mm)
                used = 1
                isTime = False
                if word_prev == 'ora':
                    words[idx - 1] = ''

            if time_qualifier != '':
                # military = True
                if str_hh and int(str_hh) <= 12 and \
                        (time_qualifier in time_qualifiers_pm):
                    str_hh = str(int(str_hh) + 12)
            else:
                isTime = False

            str_hh = int(str_hh) if str_hh else 0
            str_mm = int(str_mm) if str_mm else 0

            str_hh = str_hh + 12 if remainder == 'pm' \
                and str_hh < 12 else str_hh
            str_hh = str_hh - 12 if remainder == 'am' \
                and str_hh >= 12 else str_hh

            if (not military and
                    remainder not in ['am', 'pm'] and
                    ((not day_specified) or day_offset < 1)):
                # ambiguous time, detect whether they mean this evening or
                # the next morning based on whether it has already passed
                hr_abs = str_hh
                if anchorDate.hour < str_hh:
                    pass  # No modification needed
                elif anchorDate.hour < str_hh + 12:
                    str_hh += 12
                    hr_abs = str_hh
                else:
                    # has passed, assume the next morning
                    day_offset += 1

            if time_qualifier in time_qualifiers_pm and str_hh < 12:
                str_hh += 12

            if str_hh > 24 or str_mm > 59:
                isTime = False
                used = 0
            if isTime:
                hr_abs = str_hh * 1
                min_abs = str_mm * 1
                used += 1

            if (hr_abs or 0) <= 12 and (time_qualifier == 'sera' or
                                        time_qualifier == 'pomeriggio'):
                hr_abs = (hr_abs or 0) + 12

        if used > 0:
            # removed parsed words from the sentence
            for i in range(used):
                words[idx + i] = ''

            if word_prev == 'o' or word_prev == 'oh':
                words[words.index(word_prev)] = ''

            if idx > 0 and word_prev in markers:
                words[idx - 1] = ''
            if idx > 1 and word_prev_prev in markers:
                words[idx - 2] = ''

            idx += used - 1
            found = True

    # check that we found a date
    if not date_found:
        return None

    if day_offset is False:
        day_offset = 0

    # perform date manipulation

    extracted_date = anchorDate.replace(microsecond=0)

    if datestr != '':
        en_months = ['january', 'february', 'march', 'april', 'may', 'june',
                     'july', 'august', 'september', 'october', 'november',
                     'december']
        en_months_short = ['jan', 'feb', 'mar', 'apr', 'may', 'june', 'july',
                           'aug', 'sept', 'oct', 'nov', 'dec']

        for idx, en_month in enumerate(en_months):
            datestr = datestr.replace(months[idx], en_month)

        for idx, en_month in enumerate(en_months_short):
            datestr = datestr.replace(months_short[idx], en_month)

        try:
            temp = datetime.strptime(datestr, '%B %d')
        except ValueError:
            # Try again, allowing the year
            temp = datetime.strptime(datestr, '%B %d %Y')
        extracted_date = extracted_date.replace(hour=0, minute=0, second=0)
        if not has_year:
            temp = temp.replace(year=extracted_date.year,
                                tzinfo=extracted_date.tzinfo)
            if extracted_date < temp:
                extracted_date = extracted_date.replace(
                    year=int(current_year),
                    month=int(temp.strftime('%m')),
                    day=int(temp.strftime('%d')),
                    tzinfo=extracted_date.tzinfo)
            else:
                extracted_date = extracted_date.replace(
                    year=int(current_year) + 1,
                    month=int(temp.strftime('%m')),
                    day=int(temp.strftime('%d')),
                    tzinfo=extracted_date.tzinfo)
        else:
            extracted_date = extracted_date.replace(
                year=int(temp.strftime('%Y')),
                month=int(temp.strftime('%m')),
                day=int(temp.strftime('%d')),
                tzinfo=extracted_date.tzinfo)
    else:
        # ignore the current HH:MM:SS if relative using days or greater
        if hr_offset == 0 and min_offset == 0 and sec_offset == 0:
            extracted_date = extracted_date.replace(hour=0, minute=0, second=0)

    if year_offset != 0:
        extracted_date = extracted_date + relativedelta(years=year_offset)
    if month_offset != 0:
        extracted_date = extracted_date + relativedelta(months=month_offset)
    if day_offset != 0:
        extracted_date = extracted_date + relativedelta(days=day_offset)
    if hr_abs != -1 and min_abs != -1:
        # If no time was supplied in the string set the time to default
        # time if it's available
        if hr_abs is None and min_abs is None and default_time is not None:
            hr_abs, min_abs = default_time.hour, default_time.minute
        else:
            hr_abs = hr_abs or 0
            min_abs = min_abs or 0

        extracted_date = extracted_date + relativedelta(hours=hr_abs,
                                                        minutes=min_abs)
        if (hr_abs != 0 or min_abs != 0) and datestr == '':
            if not day_specified and anchorDate > extracted_date:
                extracted_date = extracted_date + relativedelta(days=1)
    if hr_offset != 0:
        extracted_date = extracted_date + relativedelta(hours=hr_offset)
    if min_offset != 0:
        extracted_date = extracted_date + relativedelta(minutes=min_offset)
    if sec_offset != 0:
        extracted_date = extracted_date + relativedelta(seconds=sec_offset)

    words = [x for x in words if x not in noise_words_2]
    words = [x for x in words if x]
    result_str = ' '.join(words)

    return [extracted_date, result_str]


def get_gender_it(word, context=""):
    """
    In Italian to define the grammatical gender of a word is necessary
    analyze the article that precedes the word and not only the last
    letter of the word.
    """

    gender = None
    words = context.split(' ')
    for idx, w in enumerate(words):
        if w == word and idx != 0:
            previous = words[idx - 1]
            gender = get_gender_it(previous)
            break

    if not gender:
        if word[-1] == 'a' or word[-1] == 'e':
            gender = 'f'
        if word[-1] == 'o' or word[-1] == 'n' \
                or word[-1] == 'l' or word[-1] == 'i':
            gender = 'm'

    return gender


def extract_numbers_it(text, short_scale=False, ordinals=False):
    """
        Takes in a string and extracts a list of numbers.

    Args:
        text (str): the string to extract a number from
        short_scale (bool): Use "short scale" or "long scale" for large
            numbers -- over a million.  The default is short scale, which
            is now common in most English speaking countries.
            See https://en.wikipedia.org/wiki/Names_of_large_numbers
        ordinals (bool): consider ordinal numbers, e.g. third=3 instead of 1/3
    Returns:
        list: list of extracted numbers as floats
    """
    return extract_numbers_generic(text, pronounce_number_it,
                                   extract_number_it,
                                   short_scale=short_scale, ordinals=ordinals)


class ItalianNormalizer(Normalizer):
    """ TODO implement language specific normalizer"""
