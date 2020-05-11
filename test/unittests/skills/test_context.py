from unittest import TestCase, mock

from mycroft.skills.context import adds_context, removes_context
"""
Tests for the adapt context decorators.
"""


class ContextSkillMock(mock.Mock):
    """Mock class to apply decorators on."""
    @adds_context('DestroyContext')
    def handler_adding_context(self):
        pass

    @adds_context('DestroyContext', 'exterminate')
    def handler_adding_context_with_words(self):
        pass

    @removes_context('DestroyContext')
    def handler_removing_context(self):
        pass


class TestContextDecorators(TestCase):
    def test_adding_context(self):
        """Check that calling handler adds the correct Keyword."""
        skill = ContextSkillMock()
        skill.handler_adding_context()
        skill.set_context.assert_called_once_with('DestroyContext', '')

    def test_adding_context_with_words(self):
        """Ensure that decorated handler adds Keyword and content."""
        skill = ContextSkillMock()
        skill.handler_adding_context_with_words()
        skill.set_context.assert_called_once_with('DestroyContext',
                                                  'exterminate')

    def test_removing_context(self):
        """Make sure the decorated handler removes the specified context."""
        skill = ContextSkillMock()
        skill.handler_removing_context()
        skill.remove_context.assert_called_once_with('DestroyContext')
