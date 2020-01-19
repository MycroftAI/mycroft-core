from unittest import TestCase, mock

from mycroft.messagebus import Message
from mycroft.skills.common_play_skill import CommonPlaySkill, CPSMatchLevel
from mycroft.skills.audioservice import AudioService


class AnyCallable:
    """Class matching any callable.

    Useful for assert_called_with arguments.
    """
    def __eq__(self, other):
        return callable(other)


class TestCommonPlay(TestCase):
    def setUp(self):
        self.skill = CPSTest()
        self.bus = mock.Mock(name='bus')
        self.skill.bind(self.bus)
        self.audioservice = mock.Mock(name='audioservice')
        self.skill.audioservice = self.audioservice

    def test_lifecycle(self):
        skill = CPSTest()
        bus = mock.Mock(name='bus')
        skill.bind(bus)
        self.assertTrue(isinstance(skill.audioservice, AudioService))
        bus.on.assert_any_call('play:query', AnyCallable())
        bus.on.assert_any_call('play:start', AnyCallable())
        skill.shutdown()

    def test_handle_start_playback(self):
        """Test common play start method."""
        self.skill.audioservice.is_playing = True
        start_playback = self.bus.on.call_args_list[-1][0][1]

        phrase = 'Don\'t open until doomsday'
        start_playback(Message('play:start', data={'phrase': phrase,
                                                   'skill_id': 'asdf'}))
        self.skill.CPS_start.assert_not_called()

        self.bus.emit.reset_mock()
        start_playback(Message('play:start',
                               data={'phrase': phrase,
                                     'skill_id': self.skill.skill_id}))
        self.audioservice.stop.assert_called_once_with()
        self.skill.CPS_start.assert_called_once_with(phrase, None)

    def test_cps_play(self):
        """Test audioservice play helper."""
        self.skill.play_service_string = 'play on godzilla'
        self.skill.CPS_play(['looking_for_freedom.mp3'],
                            utterance='play on mothra')
        self.audioservice.play.assert_called_once_with(
            ['looking_for_freedom.mp3'], utterance='play on mothra')

        self.audioservice.play.reset_mock()
        # Assert that the utterance is injected
        self.skill.CPS_play(['looking_for_freedom.mp3'])
        self.audioservice.play.assert_called_once_with(
            ['looking_for_freedom.mp3'], utterance='play on godzilla')

    def test_stop(self):
        """Test default reaction to stop command."""
        self.audioservice.is_playing = False
        self.assertFalse(self.skill.stop())

        self.audioservice.is_playing = True
        self.assertTrue(self.skill.stop())


class TestCPSQuery(TestCase):
    def setUp(self):
        self.skill = CPSTest()
        self.bus = mock.Mock(name='bus')
        self.skill.bind(self.bus)
        self.audioservice = mock.Mock(name='audioservice')
        self.skill.audioservice = self.audioservice
        self.query_phrase = self.bus.on.call_args_list[-2][0][1]

    def test_handle_play_query_no_match(self):
        """Test common play match when no match is found."""

        # Check Not matching queries
        self.skill.CPS_match_query_phrase.return_value = None
        self.query_phrase(Message('play:query',
                                  data={'phrase': 'Monster mash'}))

        # Check that the skill replied that it was searching
        extension = self.bus.emit.call_args_list[-2][0][0]
        self.assertEqual(extension.data['phrase'], 'Monster mash')
        self.assertEqual(extension.data['skill_id'], self.skill.skill_id)
        self.assertEqual(extension.data['searching'], True)

        # Assert that the skill reported that it couldn't find the phrase
        response = self.bus.emit.call_args_list[-1][0][0]
        self.assertEqual(response.data['phrase'], 'Monster mash')
        self.assertEqual(response.data['skill_id'], self.skill.skill_id)
        self.assertEqual(response.data['searching'], False)

    def test_play_query_match(self):
        """Test common play match when a match is found."""
        phrase = 'Don\'t open until doomsday'
        self.skill.CPS_match_query_phrase.return_value = (phrase,
                                                          CPSMatchLevel.TITLE)
        self.query_phrase(Message('play:query',
                                  data={'phrase': phrase}))
        # Assert that the skill reported the correct confidence
        response = self.bus.emit.call_args_list[-1][0][0]
        self.assertEqual(response.data['phrase'], phrase)
        self.assertEqual(response.data['skill_id'], self.skill.skill_id)
        self.assertAlmostEqual(response.data['conf'], 0.85)

        # Partial phrase match
        self.skill.CPS_match_query_phrase.return_value = ('until doomsday',
                                                          CPSMatchLevel.TITLE)
        self. query_phrase(Message('play:query',
                                   data={'phrase': phrase}))
        # Assert that the skill reported the correct confidence
        response = self.bus.emit.call_args_list[-1][0][0]
        self.assertEqual(response.data['phrase'], phrase)
        self.assertEqual(response.data['skill_id'], self.skill.skill_id)
        self.assertAlmostEqual(response.data['conf'], 0.825)


class CPSTest(CommonPlaySkill):
    """Simple skill for testing the CommonPlaySkill"""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.CPS_match_query_phrase = mock.Mock(name='match_phrase')
        self.CPS_start = mock.Mock(name='start_playback')
        self.skill_id = 'CPSTest'

    def CPS_match_query_phrase(self, phrase):
        pass

    def CPS_start(self, data):
        pass
