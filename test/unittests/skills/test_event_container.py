import unittest
from unittest import mock

from mycroft.skills.mycroft_skill.event_container import EventContainer


def example_handler(message):
    pass


class TestEventContainer(unittest.TestCase):
    def test_init(self):
        bus = mock.MagicMock()

        # Set bus via init
        container = EventContainer(bus)
        self.assertEqual(container.bus, bus)

        # Set bus using .set_bus
        container = EventContainer(None)
        self.assertEqual(container.bus, None)
        container.set_bus(bus)
        self.assertEqual(container.bus, bus)

    def test_add(self):
        bus = mock.MagicMock()
        container = EventContainer(bus)
        self.assertEqual(len(container.events), 0)

        # Test add normal event handler
        container.add('test1', example_handler)
        self.assertTrue(bus.on.called)

        # Test add single shot event handler
        len_before = len(container.events)
        container.add('test2', example_handler, once=True)
        self.assertEqual(len_before + 1, len(container.events))
        self.assertTrue(bus.once.called)

        # Verify correct content in event container
        self.assertTrue(('test1', example_handler) in container.events)
        self.assertEqual(len(container.events), 2)

    def test_remove(self):
        bus = mock.MagicMock()
        container = EventContainer(bus)
        self.assertEqual(len(container.events), 0)

        container.add('test1', example_handler)
        container.add('test2', example_handler)
        container.add('test3', example_handler)
        self.assertEqual(len(container.events), 3)

        self.assertTrue(('test2', example_handler) in container.events)
        container.remove('test2')
        self.assertTrue(('test2', example_handler) not in container.events)
        self.assertTrue(bus.remove_all_listeners.called)

    def test_clear(self):
        bus = mock.MagicMock()
        container = EventContainer(bus)

        container.add('test1', example_handler)
        container.add('test2', example_handler)
        container.add('test3', example_handler)
        self.assertEqual(len(container.events), 3)

        container.clear()
        self.assertEqual(len(container.events), 0)
