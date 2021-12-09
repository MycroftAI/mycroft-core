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

from mycroft.client.speech.hotword_factory import HotWordFactory


class PocketSphinxTest(unittest.TestCase):
    def testDefault(self):
        config = {
            'hey mycroft': {
                'module': 'pocketsphinx',
                'phonemes': 'HH EY . M AY K R AO F T',
                'threshold': 1e-90
            }
        }
        p = HotWordFactory.create_hotword('hey mycroft', config)
        config = config['hey mycroft']
        self.assertEqual(config['phonemes'], p.phonemes)
        self.assertEqual(config['threshold'], p.threshold)

    def testInvalid(self):
        config = {
            'hey Zeds': {
                'module': 'pocketsphinx',
                'phonemes': 'ZZZZZZZZZ',
                'threshold': 1e-90
            }
        }
        p = HotWordFactory.create_hotword('hey Zeds', config)
        self.assertEqual(p.phonemes, 'HH EY . M AY K R AO F T')
        self.assertEqual(p.key_phrase, 'hey mycroft')

    def testVictoria(self):
        config = {
            'hey victoria': {
                'module': 'pocketsphinx',
                'phonemes': 'HH EY . V IH K T AO R IY AH',
                'threshold': 1e-90
            }
        }
        p = HotWordFactory.create_hotword('hey victoria', config)
        config = config['hey victoria']
        self.assertEqual(config['phonemes'], p.phonemes)
        self.assertEqual(p.key_phrase, 'hey victoria')
