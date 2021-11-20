# backwards compat import for mycroft-core
# this code is maintained as part of ovos_utils
from ovos_utils.log import LOG


def getLogger(name="MYCROFT"):
    """Depreciated. Use LOG instead"""
    return LOG
