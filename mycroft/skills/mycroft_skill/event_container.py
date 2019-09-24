from inspect import signature

from mycroft.messagebus.message import Message
from mycroft.metrics import Stopwatch, report_timing
from mycroft.util.log import LOG

from ..skill_data import to_alnum


def unmunge_message(message, skill_id):
    """Restore message keywords by removing the Letterified skill ID.
    Arguments:
        message (Message): Intent result message
        skill_id (str): skill identifier
    Returns:
        Message without clear keywords
    """
    if isinstance(message, Message) and isinstance(message.data, dict):
        skill_id = to_alnum(skill_id)
        for key in list(message.data.keys()):
            if key.startswith(skill_id):
                # replace the munged key with the real one
                new_key = key[len(skill_id):]
                message.data[new_key] = message.data.pop(key)

    return message


def get_handler_name(handler):
    """Name (including class if available) of handler function.

    Arguments:
        handler (function): Function to be named

    Returns:
        string: handler name as string
    """
    if '__self__' in dir(handler) and 'name' in dir(handler.__self__):
        return handler.__self__.name + '.' + handler.__name__
    else:
        return handler.__name__


def create_wrapper(handler, skill_id, on_start, on_end, on_error):
    """Create the default skill handler wrapper.

    This wrapper handles things like metrics, reporting handler start/stop
    and errors.
        handler (callable): method/function to call
        skill_id: skill_id for associated skill
        on_start (function): function to call before executing the handler
        on_end (function): function to call after executing the handler
        on_error (function): function to call for error reporting
    """
    def wrapper(message):
        stopwatch = Stopwatch()
        try:
            message = unmunge_message(message, skill_id)
            if on_start:
                on_start(message)

            with stopwatch:
                if len(signature(handler).parameters) == 0:
                    handler()
                else:
                    handler(message)

        except Exception as e:
            if on_error:
                on_error(e)
        finally:
            if on_end:
                on_end(message)

            # Send timing metrics
            context = message.context
            if context and 'ident' in context:
                report_timing(context['ident'], 'skill_handler', stopwatch,
                              {'handler': handler.__name__,
                               'skill_id': skill_id})
    return wrapper


def create_basic_wrapper(handler, on_error=None):
    """Create the default skill handler wrapper.

    This wrapper handles things like metrics, reporting handler start/stop
    and errors.

    Arguments:
        handler (callable): method/function to call
        on_error (function): function to call to report error.

    Returns:
        Wrapped callable
    """
    def wrapper(message):
        try:
            if len(signature(handler).parameters) == 0:
                handler()
            else:
                handler(message)
        except Exception as e:
            if on_error:
                on_error(e)

    return wrapper


class EventContainer:
    """Container tracking messagbus handlers.

    This container tracks events added by a skill, allowing unregistering
    all events on shutdown.
    """
    def __init__(self, bus=None):
        self.bus = bus
        self.events = []

    def set_bus(self, bus):
        self.bus = bus

    def add(self, name, handler, once=False):
        """Create event handler for executing intent or other event.

        Arguments:
            name (string): IntentParser name
            handler (func): Method to call
            once (bool, optional): Event handler will be removed after it has
                                   been run once.
        """
        def once_wrapper(message):
            # Remove registered one-time handler before invoking,
            # allowing them to re-schedule themselves.
            handler(message)
            self.remove(name)

        if handler:
            if once:
                self.bus.once(name, once_wrapper)
            else:
                self.bus.on(name, handler)
            self.events.append((name, handler))

    def remove(self, name):
        """Removes an event from bus emitter and events list.

        Args:
            name (string): Name of Intent or Scheduler Event
        Returns:
            bool: True if found and removed, False if not found
        """
        print("Removing event {}".format(name))
        removed = False
        for _name, _handler in list(self.events):
            if name == _name:
                try:
                    self.events.remove((_name, _handler))
                except ValueError:
                    LOG.error('Failed to remove event {}'.format(name))
                    pass
                removed = True

        # Because of function wrappers, the emitter doesn't always directly
        # hold the _handler function, it sometimes holds something like
        # 'wrapper(_handler)'.  So a call like:
        #     self.bus.remove(_name, _handler)
        # will not find it, leaving an event handler with that name left behind
        # waiting to fire if it is ever re-installed and triggered.
        # Remove all handlers with the given name, regardless of handler.
        if removed:
            self.bus.remove_all_listeners(name)
        return removed

    def __iter__(self):
        return iter(self.events)

    def clear(self):
        """Unregister all registered handlers and clear the list of registered
        events.
        """
        for e, f in self.events:
            self.bus.remove(e, f)
        self.events = []  # Remove reference to wrappers
