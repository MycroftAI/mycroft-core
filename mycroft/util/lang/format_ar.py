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

from mycroft.util.lang.format_common import convert_to_mixed_fraction
from mycroft.util.log import LOG
from mycroft.util.lang.common_data_ar import _NUM_STRING_AR, _FRACTION_STRING_AR, _LONG_SCALE_AR, _SHORT_SCALE_AR, _NUM_HOUR_AR


def nice_number_en(number, speech, denominators):
    """ English helper for nice_number

    This function formats a float to human understandable functions. Like
    4.5 becomes "4 and a half" for speech and "4 1/2" for text

    Args:
        number (int or float): the float to format
        speech (bool): format for speech (True) or display (False)
        denominators (iter of ints): denominators to use, default [1 .. 20]
    Returns:
        (str): The formatted string.
    """

    result = convert_to_mixed_fraction(number, denominators)
    if not result:
        # Give up, just represent as a 3 decimal number
        return str(round(number, 3))

    whole, num, den = result

    if not speech:
        if num == 0:
            # TODO: Number grouping?  E.g. "1,000,000"
            return str(whole)
        else:
            return '{} {}/{}'.format(whole, num, den)

    if num == 0:
        return str(whole)
    den_str = _FRACTION_STRING_EN[den]
    if whole == 0:
        if num == 1:
            return_string = 'a {}'.format(den_str)
        else:
            return_string = '{} {}'.format(num, den_str)
    elif num == 1:
        return_string = '{} and a {}'.format(whole, den_str)
    else:
        return_string = '{} and {} {}'.format(whole, num, den_str)
    if num > 1:
        return_string += 's'
    return return_string


def pronounce_number_ar(num, places=2, short_scale=False, scientific=False):
    """
    Convert a number to its spoken equivalent

    For example, '28' would return 'ثمانية وعشرون'

    Args:
        num(float or int): the number to pronounce (under 100)
        places(int): maximum decimal places to speak
        short_scale (bool) : use short (True) or long scale (False)
            https://en.wikipedia.org/wiki/Names_of_large_numbers
        scientific (bool): pronounce in scientific notation
    Returns:
        (str): The pronounced number
    """
    """numStr = str(num).replace(',','')
    num = int(numStr.replace(' ', ''))"""
    
    if scientific:
        number = '%E' % num
        n, power = number.replace("+", "").split("E")
        power = int(power)
        if power != 0:
            # This handles negatives of powers separately from the normal
            # handling since each call disables the scientific flag
            return '{}{} قوة عشرة {}{}'.format(
                'negative ' if float(n) < 0 else '',
                pronounce_number_ar(abs(float(n)), places, short_scale, False),
                'negative ' if power < 0 else '',
                pronounce_number_ar(abs(power), places, short_scale, False))
    if short_scale:
        number_names = _NUM_STRING_AR.copy()
        number_names.update(_SHORT_SCALE_AR)
    else:
        number_names = _NUM_STRING_AR.copy()
        number_names.update(_LONG_SCALE_AR)

    digits = [number_names[n] for n in range(0, 20)]

    tens = [number_names[n] for n in range(10, 100, 10)]

    if short_scale:
        hundreds = [_SHORT_SCALE_AR[n] for n in _SHORT_SCALE_AR.keys()]
    else:
        hundreds = [_LONG_SCALE_AR[n] for n in _LONG_SCALE_AR.keys()]

    # deal with negatives
    result = ""
    if num < 0:
        result = "negative " if scientific else "minus "
    num = abs(num)

    try:
        # deal with 4 digits
        # usually if it's a 4 digit num it should be said like a date
        # i.e. 1972 => nineteen seventy two
        if len(str(num)) == 4 and isinstance(num, int):
            _num = str(num)
            # deal with 1000, 2000, 2001, 2100, 3123, etc
            # is skipped as the rest of the
            # functin deals with this already
            if _num[1:4] == '000' or _num[1:3] == '00' or int(_num[0:2]) >= 20:
                pass
            # deal with 1900, 1300, etc
            # i.e. 1900 => nineteen hundred
            elif _num[2:4] == '00':
                first = number_names[1000]
                second = number_names[int(_num[1])]
                last = number_names[100]
                return first + " و " + second + " "+ last
            # deal with 1960, 1961, etc
            # i.e. 1960 => nineteen sixty
            #      1961 => nineteen sixty one
            else:
                first = number_names[1000]
                if _num[3:4] == '0':
                    second = number_names[int(_num[1])]
                    third = number_names[100]
                    last = number_names[int(_num[2:4])]
                else:
                    second = number_names[int(_num[2:3])*10]
                    last = second + " " + number_names[int(_num[3:4])]
                return first + " و " + second + third + " و " + last
    # exception used to catch any unforseen edge cases
    # will default back to normal subroutine
    except Exception as e:
        LOG.error('Exception in pronounce_number_en: {}' + repr(e))

    # check for a direct match
    if num in number_names:
       
        result += number_names[num]
    else:
        def _sub_thousand(n):
            
            assert 0 <= n <= 999
            if n <= 19:
                return digits[n]
            elif n <= 99:
                q, r = divmod(n, 10)
                return ("  " + _sub_thousand(r) + " و "  if r else "") + tens[q - 1] + " "
            else:
                q, r = divmod(n, 100)
                if q == 1:
                    return "مئة و "+ (
                     _sub_thousand(r) if r else "")
                elif q == 2:
                    return "مئتان و "+ (
                     _sub_thousand(r) if r else "")
                else:
                    number = digits[q]
                    return number[0:len(number)-1] + " مئة و "+ (
                         _sub_thousand(r) if r else "")



        def _short_scale(n):
            if n >= max(_SHORT_SCALE_AR.keys()):
                return "infinity"
            n = int(n)
            assert 0 <= n
            res = []
            
            for i, z in enumerate(_split_by(n, 1000)):
                if not z:
                    continue
                number = _sub_thousand(z)
                if i:
                    if z==1:
                        number = 'ألف'
                    elif z==2:
                        number = 'ألفان'
                    elif z>2 and z<11:
                        number += " "
                        number += 'آلاف'
                    else:
                        number += " "
                        number += 'ألف'
                    
                    
                res.append(number)

            return " و ".join(reversed(res))

        def _long_scale(n):
            if n >= max(_LONG_SCALE_AR.keys()):
                return "infinity"
            n = int(n)
            assert 0 <= n
            res = []
            for i, z in enumerate(_split_by(n, 1000000)):
                if not z:
                    continue
                
                number = pronounce_number_ar(z, places, True, scientific)
                # strip off the comma after the thousand
                if i: 
                    number =_sub_thousand(z)
                    if z==1:
                        number = 'مليون'
                    elif z==2:
                        number = 'مليونين'
                    elif z>2 and z<11  :
                        number += " "
                        number += 'ملايين'
                    else :
                        number += " "
                        number += 'مليون'

                    # plus one as we skip 'thousand'
                    # (and 'hundred', but this is excluded by index value)
                    #number = number.replace(',', '')
                    #number += " " + hundreds[i+1]
                res.append(number)
            return " و ".join(reversed(res))

        def _split_by(n, split=1000):
            assert 0 <= n
            res = []
            while n:
                n, r = divmod(n, split)
              
                res.append(r)
            return res



        if short_scale:
            result += _short_scale(num)
        else:
            result += _long_scale(num)

    # Deal with fractional part
    if not num == int(num) and places > 0:
        before, sep, after = str(num).rpartition(".")
        if not int(before)==0:
            result = _sub_thousand(int(before))
            result += " و "
        placesVar = places
        place = 10
            
        
        if len(after) == 1:
            result += " " + _sub_thousand(int(after[:1]))
            result += " من عشرة "
        elif len(after) == 2:
            result += " " + _sub_thousand(int(after[0:2]))
            result +=  " من مئة "
        elif len(after) == 3:
            result += " " + _sub_thousand(int(after[0:3]))
            result += " من ألف "
          



    return result


def nice_time_ar(dt, speech=True, use_24hour=False, use_ampm=True):
    """
    Format a time to a comfortable spoken format

    For example, generate 'السابعة وثلاثة عشر دقيقة' for speech or '7:13' for
    text display.

    Args:
        dt (datetime): date to format (assumes already in local timezone)
        speech (bool): format for speech (default/True) or display (False)=Fal
        use_24hour (bool): output in 24-hour/military or 12-hour format
        use_ampm (bool): include the am/pm for 12-hour format
    Returns:
        (str): The formatted time string
    """
    if use_24hour:
        # e.g. "03:01" or "14:22"
        string = dt.strftime("%H:%M")
    else:
        if use_ampm:
            # e.g. "3:01 AM" or "2:22 PM"
            string = dt.strftime("%I:%M %p")
        else:
            # e.g. "3:01" or "2:22"
            string = dt.strftime("%I:%M")
        if string[0] == '0':
            string = string[1:]  # strip leading zeros

    if not speech:
        return string

    # Generate a speakable version of the time
    if use_24hour:
        speak = ""

        # Either "0 8 hundred" or "13 hundred"
        if string[0] == '0':
            speak += pronounce_number_ar(int(string[0])) + " "
            speak += pronounce_number_ar(int(string[1]))
        else:
            speak = pronounce_number_ar(int(string[0:2]))

        speak += " "
        if string[3:5] == '00':
            speak += "hundred"
        else:
            if string[3] == '0':
                speak += pronounce_number_ar(0) + " "
                speak += pronounce_number_ar(int(string[4]))
            else:
                speak += pronounce_number_ar(int(string[3:5]))
        return speak
    #In our version we do not use 24hours, but we can change it, so we will us this part of the code
    else: 
        """check if the given time is zeros, 00:00, then it is 12 a.m"""
        if dt.hour == 0 and dt.minute == 0:
            return "الساعة الثانية عشر صباحاً"
        """check if the given time is 12:00, then it is 12 pm"""
        if dt.hour == 12 and dt.minute == 0:
            return "الساعة الثانية عشر ظهراً"
       
         #else (having another cases than the above), then first check the hours, and based on its value send it the pronounce hour function to return the number in digit and concatenate it 
         #with الساعة i.e. if hours = 11, then it will be الساعة الحادية عشر
        if dt.hour == 0:
            speak = "الساعة "+ pronounce_hour_ar(12)
        elif dt.hour < 13:
            speak = "الساعة "+ pronounce_hour_ar(dt.hour)
        else:
            speak = "الساعة "+ pronounce_hour_ar(dt.hour - 12)

        """now complete checking the minutes, we might have minutes vaue as well, do the same thing and concatente it with the previous value, i.e. it will be الساعة الحادية عشر ودقيقتان"""
        if dt.minute == 0:
            if not use_ampm:
                return speak 
        else:
            if dt.minute < 11:
                if dt.minute ==1:
                    speak += " و دقيقة"
                if dt.minute ==2:
                    speak += " و دقيقتان"
                elif dt.minute >2 and dt.minute < 11:
                    speak += " و" + pronounce_number_ar(dt.minute) + "دقائق"
            else:
                speak += " و" + pronounce_number_ar(dt.minute) + " دقيقة "

                
        """when complete converting the hours and minutes to spoken form, now we need to indicate if it is a.m or p.m and add to the string مساءً - صباحاً"""
        if use_ampm:
            if dt.hour > 11:
                speak += " "+"مساءً"
            else:
                speak += " "+"صباحاً"

        return speak

"""Hours in Arabic have differend prnouncation i.e. الثانية instead of اثنين"""
def pronounce_hour_ar (num):

    hour_names = _NUM_HOUR_AR.copy()
    return hour_names[num]


