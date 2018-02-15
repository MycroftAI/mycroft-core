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
from mycroft.util.parse import normalize


class Message(object):
    """Holds and manipulates data sent over the websocket

        Message objects will be used to send information back and forth
        between processes of Mycroft.

    Attributes:
        type (str): type of data sent within the message.
        data (dict): data sent within the message
        context: info about the message not part of data such as source,
            destination or domain.
    """

    def __init__(self, type, data=None, context=None):
        """Used to construct a message object

        Message objects will be used to send information back and fourth
        bettween processes of mycroft service, voice, skill and cli
        """
        data = data or {}
        self.type = type
        self.data = data
        self.context = context

    def serialize(self):
        """This returns a string of the message info.

        This makes it easy to send over a websocket. This uses
        json dumps to generate the string with type, data and context

        Returns:
            str: a json string representation of the message.
        """
        return json.dumps({
            'type': self.type,
            'data': self.data,
            'context': self.context
        })

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
        return Message(obj.get('type'), obj.get('data'), obj.get('context'))

    def reply(self, type, data, context=None):
        """Construct a reply message for a given message

        This will take the same parameters as a message object but use
        the current message object as a reference.  It will copy the context
        from the existing message object and add any context passed in to
        the function.  Check for a target passed in to the function from
        the data object and add that to the context as a target.  If the
        context has a client name then that will become the target in the
        context.  The new message will then have data passed in plus the
        new context generated.

        Args:
            type (str): type of message
            data (dict): data for message
            context: intented context for new message

        Returns:
            Message: Message object to be used on the reply to the message
        """
        context = context or {}

        new_context = self.context if self.context else {}
        for key in context:
            new_context[key] = context[key]
        if 'target' in data:
            new_context['target'] = data['target']
        elif 'client_name' in context:
            context['target'] = context['client_name']
        return Message(type, data, context=new_context)

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
        response_message = self.reply(self.type, data or {}, context)
        response_message.type += '.response'
        return response_message

    def publish(self, type, data, context=None):
        """
        Copy the original context and add passed in context.  Delete
        any target in the new context. Return a new message object with
        passed in data and new context.  Type remains unchanged.

        Args:
            type (str): type of message
            data (dict): date to send with message
            context: context added to existing context

        Returns:
            Message: Message object to publish
        """
        context = context or {}
        new_context = self.context.copy() if self.context else {}
        for key in context:
            new_context[key] = context[key]

        if 'target' in new_context:
            del new_context['target']

        return Message(type, data, context=new_context)

    def utterance_remainder(self):
        """
        For intents get the portion not consumed by Adapt.

        For example: if they say 'Turn on the family room light' and there are
        entity matches for "turn on" and "light", then it will leave behind
        " the family room " which is then normalized to "family room".

        Returns:
            str: Leftover words or None if not an utterance.
        """
        utt = self.data.get("utterance", None)
        if utt and "__tags__" in self.data:
            for token in self.data["__tags__"]:
                utt = utt.replace(token["key"], "")
        return normalize(utt)
