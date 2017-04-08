import sys
from unittest import TestLoader

from os.path import dirname
from xmlrunner import XMLTestRunner

from mycroft.configuration import ConfigurationManager

__author__ = 'seanfitz, jdorleans'

if __name__ == "__main__":
    fail_on_error = "--fail-on-error" in sys.argv
    ConfigurationManager.load_local(['mycroft.conf'], keep_user_config=False)

    tests = TestLoader().discover(dirname(__file__), "*.py")
    result = XMLTestRunner("./build/report/tests").run(tests)

    if fail_on_error and len(result.failures + result.errors) > 0:
        sys.exit(1)
