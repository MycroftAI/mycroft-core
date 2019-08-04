import collections
import functools

from .log import LOG


# The following memoized class is copied from the PythonDecoratorLibrary at:
#     https://wiki.python.org/moin/PythonDecoratorLibrary/#Memoize
class memoized(object):
    """Decorator to cache a function's return value each time it is called.

    If called later with the same arguments, the cached value is returned
    (not reevaluated).
    """
    def __init__(self, func):
        self.func = func
        self.cache = {}

    def __call__(self, *args):
        if not isinstance(args, collections.Hashable):
            # Cannot cache if instance is not hashable (e.g. a list).
            # Better to not cache than blow up.
            LOG.error('function called with an un-hashable argument')
            return self.func(*args)
        if args in self.cache:
            LOG.info('using cached return value')
            return self.cache[args]
        else:
            LOG.info('caching function call')
            value = self.func(*args)
            self.cache[args] = value
            return value

    def __repr__(self):
        """Return the function's docstring."""
        return self.func.__doc__

    def __get__(self, obj, objtype):
        """Support instance methods."""
        return functools.partial(self.__call__, obj)
