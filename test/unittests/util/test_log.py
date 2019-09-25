# Copyright 2017 Mycroft AI Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
from contextlib import contextmanager
from io import StringIO
import unittest
from threading import Thread
from mycroft.util.log import LOG
from logging import StreamHandler


@contextmanager
def temporary_handler(log, handler):
    """Context manager to replace the default logger with a temporary logger.

    Args:
        log (LOG): mycroft LOG object
        handler (logging.Handler): Handler object to use
    """
    log.addHandler(handler)
    yield
    log.removeHandler(handler)


class TestLog(unittest.TestCase):
    def test_threads(self):
        output = StringIO()
        with temporary_handler(LOG, StreamHandler(output)):
            def test_logging():
                LOG.debug('testing debug')
                LOG.info('testing info')
                LOG.warning('testing warning')
                LOG.error('testing error')

            threads = []
            for _ in range(100):
                t = Thread(target=test_logging)
                t.start()
                threads.append(t)

            for t in threads:
                t.join()

        assert len(output.getvalue()) > 0

        for line in output:
            found_msg = False
            for msg in ['debug', 'info', 'warning', 'error', 'custom']:
                if 'testing ' + msg in line:
                    found_msg = True
            assert found_msg


if __name__ == "__main__":
    unittest.main()
