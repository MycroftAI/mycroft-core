import abc

# abstract base class for a Mycroft Volume
# all volume classes must provide at least 
# these basic methods

class MycroftVolume(object):
    __metaclass__ = abc.ABCMeta

    @abc.abstractmethod
    def set_hw_volume(self, vol):
        """takes in value between 0.0 - 1.0
           converts to internal format"""
        return

    @abc.abstractmethod
    def get_hw_volume(self):
        """returns float from internal format"""

    @abc.abstractmethod
    def get_capabilities(self):
        """returns capabilities object"""
        return

