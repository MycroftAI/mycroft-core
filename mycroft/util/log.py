__author__ = 'seanfitz'

import logging
FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
logging.basicConfig(format=FORMAT, level=logging.DEBUG)
logger = logging.getLogger("MYCROFT")
logger.setLevel(logging.DEBUG)


def getLogger(name="MYCROFT"):
    """
    Get a python logger

    :param name: Module name for the logger

    :return: an instance of logging.Logger
    """
    return logging.getLogger(name)
