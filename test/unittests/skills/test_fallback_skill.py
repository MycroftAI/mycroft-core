from unittest import TestCase, mock

from mycroft.skills import FallbackSkill


def setup_fallback(fb_class):
    fb_skill = fb_class()
    fb_skill.bind(mock.Mock(name='bus'))
    fb_skill.initialize()
    return fb_skill


class TestFallbackSkill(TestCase):
    def test_life_cycle(self):
        """Test startup and shutdown of a fallback skill.

        Ensure that an added handler is removed as part of default shutdown.
        """
        self.assertEqual(len(FallbackSkill.fallback_handlers), 0)
        fb_skill = setup_fallback(SimpleFallback)
        self.assertEqual(len(FallbackSkill.fallback_handlers), 1)
        self.assertEqual(FallbackSkill.wrapper_map[0][0],
                         fb_skill.fallback_handler)
        self.assertEqual(len(FallbackSkill.wrapper_map), 1)

        fb_skill.default_shutdown()
        self.assertEqual(len(FallbackSkill.fallback_handlers), 0)
        self.assertEqual(len(FallbackSkill.wrapper_map), 0)

    def test_manual_removal(self):
        """Test that the call to remove_fallback() removes the handler"""
        self.assertEqual(len(FallbackSkill.fallback_handlers), 0)

        # Create skill adding a single handler
        fb_skill = setup_fallback(SimpleFallback)
        self.assertEqual(len(FallbackSkill.fallback_handlers), 1)

        self.assertTrue(fb_skill.remove_fallback(fb_skill.fallback_handler))
        # Both internal trackers of handlers should be cleared now
        self.assertEqual(len(FallbackSkill.fallback_handlers), 0)
        self.assertEqual(len(FallbackSkill.wrapper_map), 0)

        # Removing after it's already been removed should fail
        self.assertFalse(fb_skill.remove_fallback(fb_skill.fallback_handler))


class SimpleFallback(FallbackSkill):
    """Simple fallback skill used for test."""
    def initialize(self):
        self.register_fallback(self.fallback_handler, 42)

    def fallback_handler(self):
        pass
