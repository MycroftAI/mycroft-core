# coding=utf-8
'''
Created on 15.08.2018

@author: Niels
'''

from quantulum import parser

def nice_unit(unit, context=None, lang='en-us'):
    """
        Format a unit to a pronouncable string
        
        Args:
            unit (string): The unit abbreviation that is to be pronounced
                (i.e. "C", "MW", "mW", "°F" etc)
            context (string): A text in which the correct meaning of this
                abbreviation becomes clear (i.e. "It's almost 30 C outside")
            lang (string): the language to use, use Mycroft default language if
            not provided
        Returns:
            (str): A fully de-abbreviated unit for insertion in a context like
                    situation (i.e. "degree Celsius", "percent")
            (object): The parsed value of the quantity
    
    """
    if unit is None or unit == '':
        return ''
    quantity = parser.parse(context or unit)
    print(quantity)
    if len(quantity) > 0:
        quantity = quantity[0]
        if (quantity.unit.name != "dimensionless" and
                quantity.uncertainty <= 0.5):
            return quantity.unit.name, quantity.value

if __name__ == '__main__':
    print(nice_unit("W", "the power was 200W"))

