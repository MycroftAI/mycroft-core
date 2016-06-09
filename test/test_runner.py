from mycroft.configuration.config import ConfigurationManager
from mycroft.configuration.config import ConfigBuilder

import unittest

from xmlrunner import XMLTestRunner
import os
import sys


__author__ = 'seanfitz'


TEST_DIR = os.path.dirname(os.path.realpath(__file__))
OUTPUT_DIR = os.path.dirname(os.path.dirname(__file__))

loader = unittest.TestLoader()
fail_on_error = "--fail-on-error" in sys.argv
ConfigurationManager.load(ConfigBuilder()
                          .base()
                          .append(os.path.join(TEST_DIR, 'config.ini')))
tests = loader.discover(TEST_DIR, pattern="*_test*.py")
runner = XMLTestRunner(output="./build/report/tests")
result = runner.run(tests)
if fail_on_error and len(result.failures + result.errors) > 0:
    sys.exit(1)
