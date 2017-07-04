import unittest
from mycroft.skills.intent_service import IntentService, ContextManager


class MockEmitter(object):
    def __init__(self):
        self.reset()

    def emit(self, message):
        self.types.append(message.type)
        self.results.append(message.data)

    def get_types(self):
        return self.types

    def get_results(self):
        return self.results

    def reset(self):
        self.types = []
        self.results = []


class ContextManagerTest(unittest.TestCase):
    emitter = MockEmitter()

    def setUp(self):
        self.context_manager = ContextManager(3)

    def test_add_context(self):
        entity = {'confidence': 1.0}
        context = 'TestContext'
        word = 'TestWord'
        print "Adding " + context
        entity['data'] = [(word, context)]
        entity['match'] = word
        entity['key'] = word

        self.assertEqual(len(self.context_manager.frame_stack), 0)
        self.context_manager.inject_context(entity)
        self.assertEqual(len(self.context_manager.frame_stack), 1)

    def test_remove_context(self):
        entity = {'confidence': 1.0}
        context = 'TestContext'
        word = 'TestWord'
        print "Adding " + context
        entity['data'] = [(word, context)]
        entity['match'] = word
        entity['key'] = word

        self.context_manager.inject_context(entity)
        self.assertEqual(len(self.context_manager.frame_stack), 1)
        self.context_manager.remove_context('TestContext')
        self.assertEqual(len(self.context_manager.frame_stack), 0)


if __name__ == '__main__':
    unittest.main()
