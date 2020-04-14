import unittest

from mycroft.skills.intent_service_interface import IntentServiceInterface


class MockEmitter:
    def __init__(self):
        self.reset()

    def emit(self, message):
        self.types.append(message.msg_type)
        self.results.append(message.data)

    def get_types(self):
        return self.types

    def get_results(self):
        return self.results

    def on(self, event, f):
        pass

    def reset(self):
        self.types = []
        self.results = []


class FunctionTest(unittest.TestCase):
    def check_emitter(self, result_list):
        for type in self.emitter.get_types():
            self.assertEqual(type, 'register_vocab')
        self.assertEqual(sorted(self.emitter.get_results(),
                                key=lambda d: sorted(d.items())),
                         sorted(result_list, key=lambda d: sorted(d.items())))
        self.emitter.reset()

    def setUp(self):
        self.emitter = MockEmitter()

    def test_register_keyword(self):
        intent_service = IntentServiceInterface(self.emitter)
        intent_service.register_adapt_keyword('test_intent', 'test')
        self.check_emitter([{'start': 'test', 'end': 'test_intent'}])

    def test_register_keyword_with_aliases(self):
        intent_service = IntentServiceInterface(self.emitter)
        intent_service.register_adapt_keyword('test_intent', 'test',
                                              ['test2', 'test3'])
        self.check_emitter([{'start': 'test', 'end': 'test_intent'},
                            {'start': 'test2', 'end': 'test_intent',
                             'alias_of': 'test'},
                            {'start': 'test3', 'end': 'test_intent',
                             'alias_of': 'test'},
                            ])

    def test_register_regex(self):
        intent_service = IntentServiceInterface(self.emitter)
        intent_service.register_adapt_regex('.*')
        self.check_emitter([{'regex': '.*'}])
