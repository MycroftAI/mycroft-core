from unittest import TestCase, mock

from mycroft.util.process_utils import (_update_log_level, bus_logging_status,
                                        create_daemon)


class TestCreateDaemon(TestCase):
    def test_create(self):
        """Make sure deamon thread is created, and runs the expected function.
        """
        thread_ran = False

        def thread_func():
            nonlocal thread_ran
            thread_ran = True

        thread = create_daemon(thread_func)
        self.assertTrue(thread.daemon)
        self.assertTrue(thread_ran)
        thread.join()

    def test_create_with_args(self):
        """Check that the args and kwargs is passed to the thread function."""
        test_args = (1, 2, 3)
        test_kwargs = {'meaning': 42, 'borg': '7 of 9'}
        passed_args = None
        passed_kwargs = None

        def thread_func(*args, **kwargs):
            nonlocal passed_args
            nonlocal passed_kwargs
            passed_args = args
            passed_kwargs = kwargs

        thread = create_daemon(thread_func, test_args, test_kwargs)
        thread.join()
        self.assertEqual(test_args, passed_args)
        self.assertEqual(test_kwargs, passed_kwargs)


@mock.patch('mycroft.util.process_utils.LOG')
class TestUpdateLogLevel(TestCase):
    def test_no_data(self, mock_log):
        mock_log.level = 'UNSET'
        log_msg = {'msg_type': 'mycroft.debug.log',
                   'data': {}}
        _update_log_level(log_msg, 'Test')
        self.assertEqual(mock_log.level, 'UNSET')

    def test_set_debug(self, mock_log):
        mock_log.level = 'UNSET'
        log_msg = {'type': 'mycroft.debug.log',
                   'data': {'level': 'DEBUG'}}
        _update_log_level(log_msg, 'Test')
        self.assertEqual(mock_log.level, 'DEBUG')

    def test_set_lowecase_debug(self, mock_log):
        mock_log.level = 'UNSET'
        log_msg = {'type': 'mycroft.debug.log',
                   'data': {'level': 'debug'}}
        _update_log_level(log_msg, 'Test')
        self.assertEqual(mock_log.level, 'DEBUG')

    def test_set_invalid_level(self, mock_log):
        mock_log.level = 'UNSET'
        log_msg = {'type': 'mycroft.debug.log',
                   'data': {'level': 'snowcrash'}}
        _update_log_level(log_msg, 'Test')
        self.assertEqual(mock_log.level, 'UNSET')

    def test_set_bus_logging(self, mock_log):
        mock_log.level = 'UNSET'
        log_msg = {'type': 'mycroft.debug.log',
                   'data': {'bus': True}}
        self.assertFalse(bus_logging_status())
        _update_log_level(log_msg, 'Test')
        self.assertTrue(bus_logging_status())
