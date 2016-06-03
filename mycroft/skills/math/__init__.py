from os.path import dirname

from adapt.intent import IntentBuilder
from mycroft.skills.core import MycroftSkill
from mycroft.util.log import getLogger
import operator

__author__ = 'wolfgange3311999'

LOGGER = getLogger(__name__)


class MathSkill(MycroftSkill):
    def __init__(self):
        super(MathSkill, self).__init__(name="MathSkill")
        self.operators = {
            '+': operator.add,
            '-': operator.sub,
            '*': operator.mul,
            '/': operator.div
        }

    def initialize(self):
        self.load_data_files(dirname(__file__))
        self.register_regex('(?P<Value1>\d+)')
        self.register_regex('(?P<Value2>\d+)')

        intent = IntentBuilder("MathIntent").require("Value1").require("MathKeyword").require("Value2").build()
        self.register_intent(intent, self.handle_intent)

    @staticmethod
    def __to_string(num):
        """
        :rtype: string
        :param num: any float
        :return: a string representation of num without the trailing .0
        """
        return '{0:g}'.format(num)

    def handle_intent(self, message):
        first_val = float(message.metadata.get('Value1', 0))
        second_val = float(message.metadata.get('Value2', 0))

        operator_char = message.metadata.get('MathKeyword', 0)
        operator_func = self.operators[operator_char]
        result = operator_func(first_val, second_val)

        equation_string = self.__to_string(first_val) + ' ' + operator_char + ' ' + self.__to_string(second_val)
        answer_string = self.__to_string(result)
        self.speak_dialog('read.answer', data={'equation':equation_string,'answer':answer_string})

    def stop(self):
        pass


def create_skill():
    return MathSkill()
