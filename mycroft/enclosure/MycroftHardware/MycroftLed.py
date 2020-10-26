import abc

# abstract base class for a Mycroft Led
# all leds must provide at least these basic methods

class MycroftLed(object):
    __metaclass__ = abc.ABCMeta
    
    @abc.abstractmethod
    def set_led(self, which_led, color, immediate):
        """set the led - if immediate is false 
           it is buffered until the next show()"""
        return
    
    @abc.abstractmethod
    def fill(self, color):
        """set all leds to the supplied color"""
        return

    @abc.abstractmethod
    def show(self):
        """update leds from buffered data"""
        return

    @abc.abstractmethod
    def get_led(self, which_led):
        """returns current buffered value"""
        return

    @abc.abstractmethod
    def set_leds(self, leds):
        """updates buffer from leds and update hardware"""
        return

    @abc.abstractmethod
    def get_capabilities(self):
        """returns capabilities object"""
        return

