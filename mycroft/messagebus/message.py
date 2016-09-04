# Copyright 2016 Mycroft AI, Inc.
#
# This file is part of Mycroft Core.
#
# Mycroft Core is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Mycroft Core is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Mycroft Core.  If not, see <http://www.gnu.org/licenses/>.


import json

__author__ = 'seanfitz'


class Message(object):
    def __init__(self, type, metadata={}, context=None):
        self.type = type
        self.metadata = metadata
        self.context = context

    def serialize(self):
        return json.dumps({
            'type': self.type,
            'metadata': self.metadata,
            'context': self.context
        })

    @staticmethod
    def deserialize(json_str):
        json_message = json.loads(json_str)
        return Message(json_message.get('type'),
                       metadata=json_message.get('metadata'),
                       context=json_message.get('context'))

    def reply(self, type, metadata, context={}):
        if not context:
            context = {}
        new_context = self.context if self.context else {}
        for key in context:
            new_context[key] = context[key]
        if 'target' in metadata:
            new_context['target'] = metadata['target']
        elif 'client_name' in context:
            context['target'] = context['client_name']
        return Message(type, metadata, context=new_context)

    def publish(self, type, metadata, context={}):
        if not context:
            context = {}
        new_context = self.context.copy() if self.context else {}
        for key in context:
            new_context[key] = context[key]

        if 'target' in new_context:
            del new_context['target']

        return Message(type, metadata, context=new_context)
