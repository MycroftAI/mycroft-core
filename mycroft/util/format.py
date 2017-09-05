# -*- coding: iso-8859-15 -*-

# Copyright 2017 Mycroft AI, Inc.
#
# This file is part of Mycroft Core.
#
# Mycroft Core is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Mycroft Core is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Mycroft Core.  If not, see <http://www.gnu.org/licenses/>.

import math
from mycroft.util.parse import extractnumber, is_numeric, normalize

FRACTION_STRING_EN = {
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


def nice_number(number, lang="en-us", speech=True, denominators=None):
    """Format a float to human readable functions

    This function formats a float to human understandable functions. Like
    4.5 becomes 4 and a half for speech and 4 1/2 for text
    Args:
        number (str): the float to format
        lang (str): the code for the language text is in
        speech (bool): to return speech representation or text representation
        denominators (iter of ints): denominators to use, default [1 .. 20]
    Returns:
        (str): The formatted string.
    """
    result = convert_number(number, denominators)
    if not result:
        return str(round(number, 3))

    if not speech:
        whole, num, den = result
        if num == 0:
            return str(whole)
        else:
            return '{} {}/{}'.format(whole, num, den)

    lang_lower = str(lang).lower()
    if lang_lower.startswith("en"):
        return nice_number_en(result)

    # TODO: Normalization for other languages
    return str(number)


def nice_number_en(result):
    """ English conversion for nice_number """
    whole, num, den = result
    if num == 0:
        return str(whole)
    den_str = FRACTION_STRING_EN[den]
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


def convert_number(number, denominators):
    """ Convert floats to mixed fractions """
    int_number = int(number)
    if int_number == number:
        return int_number, 0, 1

    frac_number = abs(number - int_number)
    if not denominators:
        denominators = range(1, 21)

    for denominator in denominators:
        numerator = abs(frac_number) * denominator
        if (abs(numerator - round(numerator)) < 0.01):
            break
    else:
        return None

    return int_number, int(round(numerator)), denominator


operations = ["+", "-", "/", "*", "!", "^", "**", "exp", "log", "sqrt", "(",
              ")", "sqr", "qb", "pow", "=", "is"]


class ElementalOperation():
    def __init__(self, x=0, y=0, op="+"):
        self.constants = {"pi": math.pi}
        self.variables = {}
        self.num_1 = x
        self.num_2 = y
        self.op = str(op)

    def define_var(self, var, value="unknown"):
        self.variables[var] = str(value)

    def _operate(self, operation, x=0, y=1):
        # TODO equations
        if operation == "is":
            self.define_var(x, str(y))
            return str(x) + " = " + str(y)
        if str(x) in self.constants:
            x = self.constants[str(x)]
        if str(y) in self.constants:
            y = self.constants[str(y)]
        if str(x) in self.variables:
            x = self.variables[str(x)]
        if str(y) in self.variables:
            y = self.variables[str(y)]
        if not is_numeric(x) or not is_numeric(y):
            return str(x) + " " + operation + " " + str(y)
        x = float(x)
        y = float(y)
        if operation == "+":
            return x + y
        if operation == "/":
            return x / y
        if operation == "-":
            return x - y
        if operation == "*":
            return x * y
        if operation == "%":
            return x % y
        if operation == "sqrt":
            return math.sqrt(x)
        if operation == "!":
            return math.factorial(x)
        if operation == "log":
            return math.log(x, y)
        if operation == "exp":
            return math.exp(x)
        if operation in ["^", "**", "pow"]:
            return math.pow(x, y)
        if operation == "sqr":
            return math.pow(x, 2)
        if operation == "qb":
            return math.pow(x, 3)
        # TODO priority
        if operation == "(":
            pass
        if operation == ")":
            pass
        return None

    def get_expression(self):
        return str(self.num_1) + " " + self.op + " " + str(self.num_2)

    def operate(self):
        x = self.num_1
        y = self.num_2
        if x in self.constants:
            x = self.constants[x]
        if y in self.constants:
            y = self.constants[y]
        if x in self.variables:
            x = self.variables[x] if self.variables[x] != "unknown" else x
        if y in self.variables:
            y = self.variables[y] if self.variables[y] != "unknown" else y
        return self._operate(self.op, x, y)

    def set(self, x, y, op):
        self.num_1 = x
        self.num_2 = y
        self.op = str(op)


class StringOperation():
    def __init__(self, input_str, variables=None, nice=False, lang="en-us"):
        self.lang = lang
        self.nice = nice
        if variables is None:
            variables = {}
        self.variables = variables
        self.raw_str = input_str
        self.string = normalize(input_str, self.lang)

        if is_numeric(self.string):
            self.input_operations = [["0", "+", self.string]]
            self.chain = [self.string]
            self.result = self.chain[0]
        else:
            self.input_operations = extract_expression(self.string, self.lang)
            self.chain, self.result = self._chained_operation(
                self.input_operations)

        self._get_result()

    def _chained_operation(self, operations):
        # this operation object will contain all var definitions and be
        # re-set and re used internally
        OP = ElementalOperation()
        OP.variables = self.variables
        # prioritize operations by this order
        passes = [
            # ["="],
            ["is", "!", "exp", "log", "^", "sqrt", "**", "sqr", "qb", "pow"],
            ["*", "/", "%"],
            ["+", "-"]
        ]
        for current_pass in passes:
            for idx, op in enumerate(operations):
                if not op or op[1] not in current_pass:
                    continue
                prev_op = operations[idx - 1] if idx - 1 >= 0 else ""

                # check for numbers
                if op[0] in OP.constants:
                    op[0] = OP.constants[op[0]]
                if op[0] in OP.variables:
                    op[0] = OP.variables[op[0]]
                if op[2] in OP.constants:
                    op[2] = OP.constants[op[2]]
                if op[2] in OP.variables:
                    op[2] = OP.variables[op[2]]

                if is_numeric(op[0]) and op[1] in ["!", "exp", "sqrt", "^",
                                                   "**", "qb", "sqr", "pow",
                                                   "log"]:
                    OP.set(op[0], op[0], op[1])
                    result = OP.operate()
                    operations[idx] = [0, "+", result]
                    continue

                # chain operation
                if op[0] == "prev":
                    if prev_op and is_numeric(prev_op[2]):
                        OP.set(prev_op[2], op[2], op[1])
                        operations[idx - 1][2] = "next"
                        result = OP.operate()
                        operations[idx] = [0, "+", result]

                # all numbers, solve operation
                if is_numeric(op[0]) and is_numeric(op[2]):
                    OP.set(op[0], op[2], op[1])
                    result = OP.operate()
                    operations[idx] = [0, "+", result]
                    continue

                # handle vars
                if not is_numeric(op[0]) and not is_numeric(op[2]):
                    if op[0] == op[2]:
                        # find num
                        num = ""
                        for i in range(0, len(op[2])):
                            char = op[2][i]
                            if is_numeric(char) or char == ".":
                                num += char
                        if op[1] == "-":
                            operations[idx] = ["0", "+", "0"]
                            continue
                        if op[1] == "/":
                            operations[idx] = ["0", "+", "1"]
                            continue
                        if op[1] == "*":
                            operations[idx] = [op[0], "sqr", "next"]
                            continue
                        if op[1] == "+":
                            if not num:
                                operations[idx] = ["0", "+", "2" + op[0]]
                                continue
                            op[0] = op[0].replace(str(num), "")
                            num = str(2 * float(num))
                            if len(num) >= 3 and num[-2:] == ".0":
                                num = num[:-2]
                            operations[idx] = ["0", "+", num + op[0]]
                            continue
                            # TODO other ops ^ exp log sqr qb sqrt

                    else:
                        # find nums
                        num1 = ""
                        num2 = ""
                        var1 = 1
                        var2 = 2
                        for i in range(0, len(op[0])):
                            char = op[0][i]
                            if is_numeric(char) or char == ".":
                                num1 += char
                                var1 = op[0][i + 1:]
                        for i in range(0, len(op[2])):
                            char = op[2][i]
                            if is_numeric(char) or char == ".":
                                num2 += char
                                var2 = op[2][i + 1:]
                        if var1 == var2:
                            var = var1
                            if op[1] == "-":
                                num = str(float(num1) - float(num2))
                                if len(num) >= 3 and num[-2:] == ".0":
                                    num = num[:-2]
                                operations[idx] = ["0", "+", str(num) + var]
                                continue
                            if op[1] == "/":
                                num = str(float(num1) / float(num2))
                                if len(num) >= 3 and num[-2:] == ".0":
                                    num = num[:-2]
                                operations[idx] = ["0", "+", str(num) + var]
                                continue
                            if op[1] == "*":
                                num = str(float(num1) * float(num2))
                                if len(num) >= 3 and num[-2:] == ".0":
                                    num = num[:-2]
                                operations[idx] = ["0", "+", str(num) + var]
                                continue
                            if op[1] == "+":
                                num = str(float(num1) + float(num2))
                                if len(num) >= 3 and num[-2:] == ".0":
                                    num = num[:-2]
                                operations[idx] = ["0", "+", str(num) + var]
                                continue
                                # TODO other ops ^ exp log sqr qb sqrt
        self.variables = OP.variables
        # clean empty elements
        result = ""
        chain = []
        for op in operations:
            chain.append(op)
            for element in op:
                if element and element != "prev" and element != "next":
                    result += str(element)
        return chain, result

    def _get_result(self):
        # clean
        res = self.result
        while res and res[0] == "+":
            res = res[1:]
        res = res.replace("next", "")
        res = res.replace("prev", "")
        res = res.replace(" ", "")
        res = res.replace("+-", "-")
        res = res.replace("-+", "-")
        res = res.replace("++", "+")
        res = res.replace("--", "-")
        res = res.replace("+ -", "-")
        res = res.replace("- +", "-")
        res = res.replace("+ +", "+")
        res = res.replace("- -", "-")
        res = res.replace("/1", "")
        res = res.replace("sqr", " squared")
        res = res.replace("qb", " cubed")
        while len(res) > 2 and res[0] in ["+", "0"] and res[1] != ".":
            if res[0] == "+":
                res = res[1:]
            elif res[0] == "0":
                res = res[1:]
        if len(res) > 3:
            if res[-3:] == ".00":
                res = res[:-3]
        if len(res) > 2:
            if res[-2:] == ".0":
                res = res[:-2]
        for op in operations:
            res = res.replace(op, " " + op + " ")
        self.result = res
        return res

    def solve(self, debug=False):
        if debug:
            print "normalized string:", self.string
            print "raw string:", self.raw_str

        lang = self.lang
        OP = StringOperation(self.raw_str, lang=lang)
        res = OP.result
        variables = OP.variables
        if debug:
            print "elementar operations:", OP.input_operations
            print "result:", res
            print "chain", OP.chain
        i = 0
        depth = 5
        prev_res = ""
        while not res == prev_res and i < depth:
            prev_res = res
            OP = StringOperation(res, variables=variables, lang=lang)
            res = OP.result
            variables = OP.variables
            if debug:
                print"elementar operations:", OP.input_operations
                print"result:", res
                print "chain", OP.chain
            i += 1
        if debug:
            print "vars:", OP.variables
            print "\n"
        # make nice numbers
        if self.nice:
            words = res.split(" ")
            for idx, word in enumerate(words):
                if is_numeric(word):
                    words[idx] = nice_number(float(word))
            res = " ".join(words)
        return res


def solve_expression(string, nice=True, lang="en-us", debug=False):
    OP = StringOperation(string, lang=lang, nice=nice)
    return OP.solve(debug=debug)


def extract_expression(string, lang="en-us"):
    lang_lower = str(lang).lower()
    if lang_lower.startswith("en"):
        return extract_expression_en(string)


def extract_expression_en(string):
    expressions = {"+": ["add", "adding", "plus", "added"],
                   "-": ["subtract", "subtracting", "minus", "negative",
                         "subtracted"],
                   "/": ["divide", "dividing", "divided"],
                   "*": ["multiply", "multiplying", "times", "multiplied"],
                   "%": ["modulus"],
                   "!": ["factorial"],
                   "is": ["set"],  # TODO find better keyword for x = value
                   # "=": ["equals"],
                   "^": ["**", "^", "pow" "elevated", "power", "powered",
                         "raised"],
                   "sqr": ["squared"],
                   "sqrt": ["square_root"],
                   "qb": ["cubed", "qubed"],
                   "exp": ["exponent", "exponentiate", "exponentiated"],
                   "(": ["open"],
                   ")": ["close"]}
    # clean string
    noise_words = ["by", "and", "the", "in", "at", "a", "for", "an", "to",
                   "with", "off", "of"]

    # replace natural language expression
    for op in expressions:
        string = string.replace(op, " " + op + " ")
    words = string.replace(",", "").replace("square root",
                                            "sqrt").split(" ")

    for idx, word in enumerate(words):
        if word in noise_words:
            words[idx] = ""
        else:
            for operation in expressions:
                if word in expressions[operation]:
                    words[idx] = operation


    words = [word for word in words if word]
    exps = []
    # convert all numbers
    for idx, word in enumerate(words):
        if not word:
            continue
        if extractnumber(word):
            words[idx] = str(extractnumber(word))
        # join unknown vars nums
        if idx + 1 < len(words) and words[idx + 1] not in operations:
            # 3 x = 3x
            if is_numeric(word) and not is_numeric(words[idx + 1]):
                words[idx] = word + words[idx + 1]
                words[idx + 1] = ""
        if idx - 1 >= 0 and word not in operations:
            # 1 2 x = 1 2x
            if not is_numeric(word) and is_numeric(words[idx - 1]):
                words[idx] = words[idx - 1] + word
                words[idx - 1] = ""

    words = [word for word in words if word]

    # extract operations
    for idx, word in enumerate(words):
        if not word:
            continue
        # is an operation
        if word in expressions:
            operation = word
            if idx > 0:
                woi = words[idx - 1:idx + 2]
                words[idx - 1] = ""
                if idx + 1 < len(words):
                    words[idx + 1] = ""
                words[idx] = ""
                x = woi[0]
                try:
                    y = woi[2]
                except:
                    y = "next"
                if x == "":
                    x = "prev"
                if operation == "sqrt":
                    x = y
                exps.append([x, operation, y])
            else:
                # operation at first, is a sign
                y = words[idx + 1]
                words[idx + 1] = ""
                words[idx] = ""
                if operation == "-":
                    x = "-" + y
                    y = 0
                    operation = "+"
                    exps.append([x, operation, y])
                # or square root
                if operation == "sqrt":
                    x = y
                    y = "next"
                    exps.append([x, operation, y])
                    # TODO exponent, log

    if not exps and extractnumber(string):
        exps = [["0", "+", str(extractnumber(string))]]
    return exps
