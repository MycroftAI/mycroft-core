# Copyright 2019 Mycroft AI Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
"""The fallback skill implements a special type of skill handling
utterances not handled by the intent system.
"""
import operator
from mycroft.metrics import report_timing, Stopwatch
from mycroft.util.log import LOG


from .mycroft_skill import MycroftSkill, get_handler_name


class FallbackSkill(MycroftSkill):
    """Fallbacks come into play when no skill matches an Adapt or closely with
    a Padatious intent.  All Fallback skills work together to give them a
    view of the user's utterance.  Fallback handlers are called in an order
    determined the priority provided when the the handler is registered.

    ========   ========   ================================================
    Priority   Who?       Purpose
    ========   ========   ================================================
       1-4     RESERVED   Unused for now, slot for pre-Padatious if needed
         5     MYCROFT    Padatious near match (conf > 0.8)
      6-88     USER       General
        89     MYCROFT    Padatious loose match (conf > 0.5)
     90-99     USER       Uncaught intents
       100+    MYCROFT    Fallback Unknown or other future use
    ========   ========   ================================================

    Handlers with the numerically lowest priority are invoked first.
    Multiple fallbacks can exist at the same priority, but no order is
    guaranteed.

    A Fallback can either observe or consume an utterance. A consumed
    utterance will not be see by any other Fallback handlers.
    """
    fallback_handlers = {}
    wrapper_map = []  # Map containing (handler, wrapper) tuples

    def __init__(self, name=None, bus=None, use_settings=True):
        super().__init__(name, bus, use_settings)

        #  list of fallback handlers registered by this instance
        self.instance_fallback_handlers = []

    @classmethod
    def make_intent_failure_handler(cls, bus):
        """Goes through all fallback handlers until one returns True"""

        def handler(message):
            # indicate fallback handling start
            bus.emit(message.forward("mycroft.skill.handler.start",
                                     data={'handler': "fallback"}))

            stopwatch = Stopwatch()
            handler_name = None
            with stopwatch:
                for _, handler in sorted(cls.fallback_handlers.items(),
                                         key=operator.itemgetter(0)):
                    try:
                        if handler(message):
                            #  indicate completion
                            handler_name = get_handler_name(handler)
                            bus.emit(message.forward(
                                     'mycroft.skill.handler.complete',
                                     data={'handler': "fallback",
                                           "fallback_handler": handler_name}))
                            break
                    except Exception:
                        LOG.exception('Exception in fallback.')
                else:  # No fallback could handle the utterance
                    bus.emit(message.forward('complete_intent_failure'))
                    warning = "No fallback could handle intent."
                    LOG.warning(warning)
                    #  indicate completion with exception
                    bus.emit(message.forward('mycroft.skill.handler.complete',
                                             data={'handler': "fallback",
                                                   'exception': warning}))

            # Send timing metric
            if message.context.get('ident'):
                ident = message.context['ident']
                report_timing(ident, 'fallback_handler', stopwatch,
                              {'handler': handler_name})

        return handler

    @classmethod
    def _register_fallback(cls, handler, wrapper, priority):
        """Register a function to be called as a general info fallback
        Fallback should receive message and return
        a boolean (True if succeeded or False if failed)

        Lower priority gets run first
        0 for high priority 100 for low priority

        Arguments:
            handler (callable): original handler, used as a reference when
                                removing
            wrapper (callable): wrapped version of handler
            priority (int): fallback priority
        """
        while priority in cls.fallback_handlers:
            priority += 1

        cls.fallback_handlers[priority] = wrapper
        cls.wrapper_map.append((handler, wrapper))

    def register_fallback(self, handler, priority):
        """Register a fallback with the list of fallback handlers and with the
        list of handlers registered by this instance
        """

        def wrapper(*args, **kwargs):
            if handler(*args, **kwargs):
                self.make_active()
                return True
            return False

        self.instance_fallback_handlers.append(handler)
        self._register_fallback(handler, wrapper, priority)

    @classmethod
    def _remove_registered_handler(cls, wrapper_to_del):
        """Remove a registered wrapper.

        Arguments:
            wrapper_to_del (callable): wrapped handler to be removed

        Returns:
            (bool) True if one or more handlers were removed, otherwise False.
        """
        found_handler = False
        for priority, handler in list(cls.fallback_handlers.items()):
            if handler == wrapper_to_del:
                found_handler = True
                del cls.fallback_handlers[priority]

        if not found_handler:
            LOG.warning('No fallback matching {}'.format(wrapper_to_del))
        return found_handler

    @classmethod
    def remove_fallback(cls, handler_to_del):
        """Remove a fallback handler.

        Arguments:
            handler_to_del: reference to handler
        Returns:
            (bool) True if at least one handler was removed, otherwise False
        """
        # Find wrapper from handler or wrapper
        wrapper_to_del = None
        for h, w in cls.wrapper_map:
            if handler_to_del in (h, w):
                wrapper_to_del = w
                break

        if wrapper_to_del:
            cls.wrapper_map.remove((h, w))
            remove_ok = cls._remove_registered_handler(wrapper_to_del)
        else:
            LOG.warning('Could not find matching fallback handler')
            remove_ok = False
        return remove_ok

    def remove_instance_handlers(self):
        """Remove all fallback handlers registered by the fallback skill."""
        self.log.info('Removing all handlers...')
        while len(self.instance_fallback_handlers):
            handler = self.instance_fallback_handlers.pop()
            self.remove_fallback(handler)

    def default_shutdown(self):
        """Remove all registered handlers and perform skill shutdown."""
        self.remove_instance_handlers()
        super(FallbackSkill, self).default_shutdown()
