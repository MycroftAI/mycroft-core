from datetime import datetime
from dateutil.tz import tzfile, tzlocal, gettz
from unittest import TestCase, mock

from mycroft.util.time import (default_timezone, now_local, now_utc, to_utc,
                               to_local, to_system)

test_config = {
    'location': {
        'timezone': {
            'code': 'America/Chicago',
            'name': 'Central Standard Time',
            'dstOffset': 3600000,  # Daylight saving offset in milliseconds
            'offset': -21600000  # Timezone offset in milliseconds
        }
    }
}


@mock.patch('mycroft.configuration.Configuration')
class TestTimeFuncs(TestCase):
    def test_default_timezone(self, mock_conf):
        mock_conf.get.return_value = test_config
        self.assertEqual(default_timezone(),
                         tzfile('/usr/share/zoneinfo/America/Chicago'))
        # Test missing tz-info
        mock_conf.get.return_value = {}
        self.assertEqual(default_timezone(), tzlocal())

    @mock.patch('mycroft.util.time.datetime')
    def test_now_local(self, mock_dt, mock_conf):
        dt_test = datetime(year=1985, month=10, day=25, hour=8, minute=18)
        mock_dt.now.return_value = dt_test
        mock_conf.get.return_value = test_config

        self.assertEqual(now_local(), dt_test)

        expected_timezone = tzfile('/usr/share/zoneinfo/America/Chicago')
        mock_dt.now.assert_called_with(expected_timezone)

        now_local(tzfile('/usr/share/zoneinfo/Europe/Stockholm'))
        expected_timezone = tzfile('/usr/share/zoneinfo/Europe/Stockholm')
        mock_dt.now.assert_called_with(expected_timezone)

    @mock.patch('mycroft.util.time.datetime')
    def test_now_utc(self, mock_dt, mock_conf):
        dt_test = datetime(year=1985, month=10, day=25, hour=8, minute=18)
        mock_dt.utcnow.return_value = dt_test
        mock_conf.get.return_value = test_config

        self.assertEqual(now_utc(), dt_test.replace(tzinfo=gettz('UTC')))
        mock_dt.utcnow.assert_called_with()

    def test_to_utc(self, mock_conf):
        mock_conf.get.return_value = test_config
        dt = datetime(year=2000, month=1, day=1,
                      hour=0, minute=0, second=0,
                      tzinfo=gettz('Europe/Stockholm'))
        self.assertEqual(to_utc(dt), dt)
        self.assertEqual(to_utc(dt).tzinfo, gettz('UTC'))

    def test_to_local(self, mock_conf):
        mock_conf.get.return_value = test_config
        dt = datetime(year=2000, month=1, day=1,
                      hour=0, minute=0, second=0,
                      tzinfo=gettz('Europe/Stockholm'))
        self.assertEqual(to_local(dt), dt)
        self.assertEqual(to_local(dt).tzinfo, gettz('America/Chicago'))

    def test_to_system(self, mock_conf):
        mock_conf.get.return_value = test_config
        dt = datetime(year=2000, month=1, day=1,
                      hour=0, minute=0, second=0,
                      tzinfo=gettz('Europe/Stockholm'))
        self.assertEqual(to_system(dt), dt)
        self.assertEqual(to_system(dt).tzinfo, tzlocal())
