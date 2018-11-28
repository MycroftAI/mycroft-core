from pyee import EventEmitter
from multiprocessing.pool import ThreadPool
from collections import defaultdict


class ThreadedEventEmitter(EventEmitter):
    """ Event Emitter using the threadpool to run event functions in
        separate threads using a threadpool.
    """
    def __init__(self, threads=10):
        super().__init__()
        self.pool = ThreadPool(threads)
        self.wrappers = defaultdict(list)

    def on(self, event, f=None):
        """ Wrap on with a threaded launcher. """
        def wrapped(*args, **kwargs):
            return self.pool.apply_async(f, args, kwargs)

        w = super().on(event, wrapped)
        # Store mapping from function to wrapped function
        self.wrappers[event].append((f, wrapped))
        return w

    def once(self, event, f=None):
        """ Wrap once with a threaded launcher. """
        def wrapped(*args, **kwargs):
            return self.pool.apply_async(f, args, kwargs)

        wrapped = super().once(event, wrapped)
        self.wrappers[event].append((f, wrapped))
        return wrapped

    def remove_listener(self, event_name, func):
        """ Wrap the remove to translate from function to wrapped
            function.
        """
        for w in self.wrappers[event_name]:
            if w[0] == func:
                self.wrappers[event_name].remove(w)
                return super().remove_listener(event_name, w[1])
        # if no wrapper exists try removing the function
        return super().remove_listener(event_name, func)
