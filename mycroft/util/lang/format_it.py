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


FRACTION_STRING_IT = {
    2: 'mezz',
    3: 'terz',
    4: 'quart',
    5: 'quint',
    6: 'sest',
    7: 'settim',
    8: 'ottav',
    9: 'non',
    10: 'decim',
    11: 'undicesim',
    12: 'dodicesim',
    13: 'tredicesim',
    14: 'quattordicesim',
    15: 'quindicesim',
    16: 'sedicesim',
    17: 'diciassettesim',
    18: 'diciottesim',
    19: 'diciannovesim',
    20: 'ventesim'
}


def nice_number_it(result):
    """ Italian conversion for nice_number """
    whole, num, den = result
    if num == 0:
        return str(whole)
    # denominatore
    den_str = FRACTION_STRING_IT[den]
    # frazione
    if whole == 0:
        if num == 1:
            # un decimo
            return_string = 'un {}'.format(den_str)
        else:
            # tre mezzi
            return_string = '{} {}'.format(num, den_str)
    # interi  >10
    elif num == 1:
        # trenta e un
        return_string = '{} e un {}'.format(whole, den_str)
    # interi >10 con frazioni
    else:
        # venti e 3 decimi
        return_string = '{} e {} {}'.format(whole, num, den_str)

    # plurali
    if num > 1:
        return_string += 'i'
    else:
        return_string += 'o'

    return return_string
