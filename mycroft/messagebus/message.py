import json

__author__ = 'seanfitz'


class Message(object):
    def __init__(self, message_type, metadata={}, context=None):
        self.message_type = message_type
        self.metadata = metadata
        self.context = context

    def serialize(self):
        return json.dumps({
            'message_type': self.message_type,
            'metadata': self.metadata,
            'context': self.context
        })

    @staticmethod
    def deserialize(json_str):
        json_message = json.loads(json_str)
        return Message(json_message.get('message_type'),
                       metadata=json_message.get('metadata'),
                       context=json_message.get('context'))

    def reply(self, message_type, metadata, context={}):
        if not context:
            context = {}
        new_context = self.context if self.context else {}
        for key in context:
            new_context[key] = context[key]
        if 'target' in metadata:
            new_context['target'] = metadata['target']
        elif 'client_name' in context:
            context['target'] = context['client_name']
        return Message(message_type, metadata, context=new_context)

    def publish(self, message_type, metadata, context={}):
        if not context:
            context = {}
        new_context = self.context.copy() if self.context else {}
        for key in context:
            new_context[key] = context[key]

        if 'target' in new_context:
            del new_context['target']

        return Message(message_type, metadata, context=new_context)
