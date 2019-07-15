import sys
from unittest import TestCase
from unittest.mock import MagicMock, patch

sys.modules['padatious.util'] = MagicMock()
from mycroft.skills.__main__ import _starting_up

MAIN_MODULE = 'mycroft.skills.__main__.'


class TestSkillService(TestCase):
    def setUp(self) -> None:
        intent_mock = patch(MAIN_MODULE + 'IntentService', spec=True)
        self.intent_mock = intent_mock.start()
        self.addCleanup(intent_mock.stop)
        padatious_mock = patch(MAIN_MODULE + 'PadatiousService', spec=True)
        self.padatious_mock = padatious_mock.start()
        self.addCleanup(padatious_mock.stop)
        skill_mgr_mock = patch(MAIN_MODULE + 'SkillManager', spec=True)
        self.skill_mgr_mock = skill_mgr_mock.start()
        self.addCleanup(skill_mgr_mock.stop)
        conn_mock = patch(MAIN_MODULE + 'check_connection')
        self.conn_mock = conn_mock.start()
        self.addCleanup(conn_mock.stop)
        websocket_mock = patch(MAIN_MODULE + 'WebsocketClient', spec=True)
        self.websocket_mock = websocket_mock.start()
        self.addCleanup(websocket_mock.stop)

    def test_main(self):
        self.skill_mgr_mock.download_skills = None
        self.skill_mgr_mock.download_last_download = 0
        _starting_up()
        self.intent_mock.assert_called_once()
