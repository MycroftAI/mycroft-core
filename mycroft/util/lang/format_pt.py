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


FRACTION_STRING_PT = {
    2: 'meio',
    3: u'terço',
    4: 'quarto',
    5: 'quinto',
    6: 'sexto',
    7: u'sétimo',
    8: 'oitavo',
    9: 'nono',
    10: u'décimo',
    11: 'onze avos',
    12: 'doze avos',
    13: 'treze avos',
    14: 'catorze avos',
    15: 'quinze avos',
    16: 'dezasseis avos',
    17: 'dezassete avos',
    18: 'dezoito avos',
    19: 'dezanove avos',
    20: u'vigésimo',
    30: u'trigésimo',
    100: u'centésimo',
    1000: u'milésimo'
}


def nice_number_pt(result):
    """ Portuguese conversion for nice_number """
    whole, num, den = result
    if num == 0:
        return str(whole)
    # denominador
    den_str = FRACTION_STRING_PT[den]
    # fracções
    if whole == 0:
        if num == 1:
            # um décimo
            return_string = 'um {}'.format(den_str)
        else:
            # três meio
            return_string = '{} {}'.format(num, den_str)
    # inteiros >10
    elif num == 1:
        # trinta e um
        return_string = '{} e {}'.format(whole, den_str)
    # inteiros >10 com fracções
    else:
        # vinte e 3 décimo
        return_string = '{} e {} {}'.format(whole, num, den_str)
    # plural
    if num > 1:
        return_string += 's'
    return return_string
