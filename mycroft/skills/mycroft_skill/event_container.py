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


def create_wrapper(skill, name, handler, handler_info, on_error, once):
    def wrapper(message):
        skill_data = {'name': get_handler_name(handler)}
        stopwatch = Stopwatch()
        try:
            message = unmunge_message(message, skill.skill_id)
            # Indicate that the skill handler is starting
            if handler_info:
                # Indicate that the skill handler is starting if requested
                msg_type = handler_info + '.start'
                skill.bus.emit(message.reply(msg_type, skill_data))

            if once:
                # Remove registered one-time handler before invoking,
                # allowing them to re-schedule themselves.
                skill.remove_event(name)

            with stopwatch:
                if len(signature(handler).parameters) == 0:
                    handler()
                else:
                    handler(message)
                skill.settings.store()  # Store settings if they've changed

        except Exception as e:
            if on_error:
                on_error(e)
            # append exception information in message
            skill_data['exception'] = repr(e)
        finally:
            # Indicate that the skill handler has completed
            if handler_info:
                msg_type = handler_info + '.complete'
                skill.bus.emit(message.reply(msg_type, skill_data))

            # Send timing metrics
            context = message.context
            if context and 'ident' in context:
                report_timing(context['ident'], 'skill_handler', stopwatch,
                              {'handler': handler.__name__,
                               'skill_id': skill.skill_id})
    return wrapper


class EventContainer:
    """Container tracking messagbus handlers.

    This container tracks events added by a skill, allowing unregestering
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

        if handler:
            if once:
                self.bus.once(name, handler)
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
            self.bus.remove_all_listeners(e)
        self.events = []  # Remove reference to wrappers
