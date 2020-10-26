import abc

# abstract base class for a Mycroft Switch Array
# all switches must provide at least these basic methods

class MycroftSwitch(object):
    __metaclass__ = abc.ABCMeta

    @abc.abstractmethod
    def terminate(self):
        """terminates any underlying threads"""
        return

    @abc.abstractmethod
    def handle_action(self):
        return

    @abc.abstractmethod
    def handle_voldown(self):
        return

    @abc.abstractmethod
    def handle_volup(self):
        return

    @abc.abstractmethod
    def handle_mute(self, val):
        return

    @abc.abstractmethod
    def get_capabilities(self):
        return

