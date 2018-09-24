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
import unittest
import sys
from io import StringIO
from threading import Thread
from mycroft.util.log import LOG


class CaptureLogs(list):
    def __init__(self):
        list.__init__(self)
        self._stdout = None
        self._stringio = None

    def __enter__(self):
        self._stdout = sys.stdout
        sys.stdout = self._stringio = StringIO()
        LOG.init()
        return self

    def __exit__(self, *args):
        self.extend(self._stringio.getvalue().splitlines())
        del self._stringio    # free up some memory
        sys.stdout = self._stdout
        LOG.init()


class TestLog(unittest.TestCase):
    def test_threads(self):
        with CaptureLogs() as output:
            def test_logging():
                LOG.debug('testing debug')
                LOG.info('testing info')
                LOG.warning('testing warning')
                LOG.error('testing error')
                LOG('testing custom').debug('test')

            threads = []
            for _ in range(100):
                t = Thread(target=test_logging)
                t.start()
                threads.append(t)

            for t in threads:
                t.join()

        assert len(output) > 0

        for line in output:
            found_msg = False
            for msg in ['debug', 'info', 'warning', 'error', 'custom']:
                if 'testing ' + msg in line:
                    found_msg = True
            assert found_msg


if __name__ == "__main__":
    unittest.main()
