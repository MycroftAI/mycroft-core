from mycroft.configuration.config import LocalConf, DEFAULT_CONFIG
from copy import deepcopy

__config = LocalConf(DEFAULT_CONFIG)


# Base config to use when mocking
def base_config():
    return deepcopy(__config)


class Anything:
    """Class matching any object.

    Useful for assert_called_with arguments.
    """
    def __eq__(self, other):
        return True
