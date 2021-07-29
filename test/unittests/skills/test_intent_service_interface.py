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


class KeywordRegistrationTest(unittest.TestCase):
    def check_emitter(self, expected_message_data):
        """Verify that the registration messages matches the expected."""
        for msg_type in self.emitter.get_types():
            self.assertEqual(msg_type, 'register_vocab')
        self.assertEqual(
            sorted(self.emitter.get_results(),
                   key=lambda d: sorted(d.items())),
            sorted(expected_message_data, key=lambda d: sorted(d.items())))
        self.emitter.reset()

    def setUp(self):
        self.emitter = MockEmitter()

    def test_register_keyword(self):
        intent_service = IntentServiceInterface(self.emitter)
        intent_service.register_adapt_keyword('test_intent', 'test')
        entity_data = {'entity_value': 'test', 'entity_type': 'test_intent'}
        compatibility_data = {'start': 'test', 'end': 'test_intent'}
        expected_data = {**entity_data, **compatibility_data}
        self.check_emitter([expected_data])

    def test_register_keyword_with_aliases(self):
        # TODO 22.02: Remove compatibility data
        intent_service = IntentServiceInterface(self.emitter)
        intent_service.register_adapt_keyword('test_intent', 'test',
                                              ['test2', 'test3'])

        entity_data = {'entity_value': 'test', 'entity_type': 'test_intent'}
        compatibility_data = {'start': 'test', 'end': 'test_intent'}
        expected_initial_vocab = {**entity_data, **compatibility_data}

        alias_data = {
            'entity_value': 'test2',
            'entity_type': 'test_intent',
            'alias_of': 'test'
        }
        alias_compatibility = {'start': 'test2', 'end': 'test_intent'}
        expected_alias1 = {**alias_data, **alias_compatibility}

        alias_data2 = {
            'entity_value': 'test3',
            'entity_type': 'test_intent',
            'alias_of': 'test'
        }
        alias_compatibility2 = {'start': 'test3', 'end': 'test_intent'}
        expected_alias2 = {**alias_data2, **alias_compatibility2}

        self.check_emitter([expected_initial_vocab,
                            expected_alias1,
                            expected_alias2])

    def test_register_regex(self):
        intent_service = IntentServiceInterface(self.emitter)
        intent_service.register_adapt_regex('.*')
        self.check_emitter([{'regex': '.*'}])
