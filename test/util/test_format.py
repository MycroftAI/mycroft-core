
# -*- coding: iso-8859-15 -*-

import unittest
from mycroft.util.format import nice_number


class TestNiceNumber(unittest.TestCase):

    def test_vulgar_fractions(self):
        res = nice_number(0.25, speech=True)
        self.assertIn(res, ['quarter', 'one forth'])
        res = nice_number(0.50, speech=True)
        self.assertIn(res, ['half'])
        res = nice_number(0.75, speech=True)
        self.assertIn(res, ['three quarters', 'three forths'])
        