# Copyright 2017 Mycroft AI Inc.
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
import json
import inspect

from copy import deepcopy


class Message:
    """Holds and manipulates data sent over the websocket

        Message objects will be used to send information back and forth
        between processes of Mycroft.

    Attributes:
        msg_type (str): type of data sent within the message.
        data (dict): data sent within the message
        context: info about the message not part of data such as source,
            destination or domain.
    """
    def __init__(self, msg_type, data=None, context=None):
        """Used to construct a message object

        Message objects will be used to send information back and forth
        between processes of mycroft service, voice, skill and cli
        """
        self.msg_type = msg_type
        self.data = data or {}
        self.context = context or {}

    def serialize(self):
        """This returns a string of the message info.

        This makes it easy to send over a websocket. This uses
        json dumps to generate the string with type, data and context

        Returns:
            str: a json string representation of the message.
        """
        return json.dumps({'type': self.msg_type,
                           'data': self.data,
                           'context': self.context})

    @staticmethod
    def deserialize(value):
        """This takes a string and constructs a message object.

        This makes it easy to take strings from the websocket and create
        a message object.  This uses json loads to get the info and generate
        the message object.

        Args:
            value(str): This is the json string received from the websocket

        Returns:
            Message: message object constructed from the json string passed
            int the function.
            value(str): This is the string received from the websocket
        """
        obj = json.loads(value)
        return Message(obj.get('type') or '',
                       obj.get('data') or {},
                       obj.get('context') or {})

    def forward(self, msg_type, data=None):
        """ Keep context and forward message

        This will take the same parameters as a message object but use
        the current message object as a reference.  It will copy the context
        from the existing message object.

        Args:
            msg_type (str): type of message
            data (dict): data for message

        Returns:
            Message: Message object to be used on the reply to the message
        """
        data = data or {}
        return Message(msg_type, data, context=self.context)

    def reply(self, msg_type, data=None, context=None):
        """Construct a reply message for a given message

        This will take the same parameters as a message object but use
        the current message object as a reference.  It will copy the context
        from the existing message object and add any context passed in to
        the function.  Check for a destination passed in to the function from
        the data object and add that to the context as a destination.  If the
        context has a source then that will be swapped with the destination
        in the context.  The new message will then have data passed in plus the
        new context generated.

        Args:
            msg_type (str): type of message
            data (dict): data for message
            context: intended context for new message

        Returns:
            Message: Message object to be used on the reply to the message
        """
        data = deepcopy(data) or {}
        context = context or {}

        new_context = deepcopy(self.context)
        for key in context:
            new_context[key] = context[key]
        if 'destination' in data:
            new_context['destination'] = data['destination']
        if 'source' in new_context and 'destination' in new_context:
            s = new_context['destination']
            new_context['destination'] = new_context['source']
            new_context['source'] = s
        return Message(msg_type, data, context=new_context)

    def response(self, data=None, context=None):
        """Construct a response message for the message

        Constructs a reply with the data and appends the expected
        ".response" to the message

        Args:
            data (dict): message data
            context (dict): message context
        Returns
            (Message) message with the type modified to match default response
        """
        response_message = Message(self.msg_type + '.response', data or {},
                                   context or self.context)
        return response_message

    def publish(self, msg_type, data, context=None):
        """
        Copy the original context and add passed in context.  Delete
        any target in the new context. Return a new message object with
        passed in data and new context.  Type remains unchanged.

        Args:
            msg_type (str): type of message
            data (dict): date to send with message
            context: context added to existing context

        Returns:
            Message: Message object to publish
        """
        context = context or {}
        new_context = self.context.copy()
        for key in context:
            new_context[key] = context[key]

        if 'target' in new_context:
            del new_context['target']

        return Message(msg_type, data, context=new_context)


def dig_for_message():
    """Dig Through the stack for message."""
    stack = inspect.stack()
    # Limit search to 10 frames back
    stack = stack if len(stack) < 10 else stack[:10]
    local_vars = [frame[0].f_locals for frame in stack]
    for l in local_vars:
        if 'message' in l and isinstance(l['message'], Message):
            return l['message']
