# -*- coding: iso-8859-15 -*-
import unittest
from mycroft.util.format import solve_expression, extract_expression

__author__ = "jarbas"


class TestMathExtractFormat(unittest.TestCase):
    def test_extract_exps(self):
        self.assertEqual(
            extract_expression("one dog plus one dog plus two frogs"),
            [['1dog', '+', '1dog'], ['prev', '+', '2frogs']])

        self.assertEqual(
            extract_expression("one plus two plus one"),
            [['1', '+', '2'], ['prev', '+', '1']])

        self.assertEqual(
            extract_expression("ten factorial"),
            [['10', '!', 'next']])

        self.assertEqual(
            extract_expression("one plus pi plus x"),
            [['1', '+', 'pi'], ['prev', '+', 'x']])

        self.assertEqual(
            extract_expression("y divided by x"),
            [['y', '/', 'x']])

        self.assertEqual(
            extract_expression("one times seven plus two multiply by two"),
            [['1', '*', '7'], ['prev', '+', '2'], ['prev', '*', '2']])

        self.assertEqual(
            extract_expression("six"),
            [['0', '+', '6']])

    def test_solve_exps(self):
        self.assertEqual(
            solve_expression("one dog plus one dog plus two frogs"),
            "1dog + 1dog + 2frogs")

        self.assertEqual(
            solve_expression("one plus two plus one"),
            '4')

        self.assertEqual(
            solve_expression("ten factorial"),
            '3628800')

        self.assertEqual(
            solve_expression("one plus pi plus x"),
            "4.14159265359 + x")

        self.assertEqual(
            solve_expression("y divided by x"),
            "y / x")

        self.assertEqual(
            solve_expression("one times seven plus two multiply by two"),
            '11')

        self.assertEqual(
            solve_expression("six"),
            '6')


if __name__ == "__main__":
    unittest.main()
