# Copyright 2020 Mycroft AI Inc.
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

from unittest import TestCase

from mycroft.client.speech.mic import NoiseTracker


LOUD_TIME_LIMIT = 2.0  # Must be loud for 2 seconds
SILENCE_TIME_LIMIT = 5.0  # Time out after 5 seconds of silence
SECS_PER_BUFFER = 0.5

MIN_NOISE = 0
MAX_NOISE = 25


class TestNoiseTracker(TestCase):
    def test_no_loud_data(self):
        """Check that no loud data generates complete after silence timeout."""
        noise_tracker = NoiseTracker(MIN_NOISE, MAX_NOISE, SECS_PER_BUFFER,
                                     LOUD_TIME_LIMIT, SILENCE_TIME_LIMIT)

        num_updates_timeout = int(SILENCE_TIME_LIMIT / SECS_PER_BUFFER)
        num_low_updates = int(LOUD_TIME_LIMIT / SECS_PER_BUFFER)
        for _ in range(num_low_updates):
            noise_tracker.update(False)
            self.assertFalse(noise_tracker.recording_complete())
        remaining_until_low_timeout = num_updates_timeout - num_low_updates

        for _ in range(remaining_until_low_timeout):
            noise_tracker.update(False)
            self.assertFalse(noise_tracker.recording_complete())

        noise_tracker.update(False)
        self.assertTrue(noise_tracker.recording_complete())

    def test_silence_reset(self):
        """Check that no loud data generates complete after silence timeout."""
        noise_tracker = NoiseTracker(MIN_NOISE, MAX_NOISE, SECS_PER_BUFFER,
                                     LOUD_TIME_LIMIT, SILENCE_TIME_LIMIT)

        num_updates_timeout = int(SILENCE_TIME_LIMIT / SECS_PER_BUFFER)
        num_low_updates = int(LOUD_TIME_LIMIT / SECS_PER_BUFFER)
        for _ in range(num_low_updates):
            noise_tracker.update(False)

        # Insert a is_loud=True shall reset the silence tracker
        noise_tracker.update(True)

        remaining_until_low_timeout = num_updates_timeout - num_low_updates

        # Extra is needed for the noise to be reduced down to quiet level
        for _ in range(remaining_until_low_timeout + 1):
            noise_tracker.update(False)
            self.assertFalse(noise_tracker.recording_complete())

        # Adding low noise samples to complete the timeout
        for _ in range(num_low_updates + 1):
            noise_tracker.update(False)
        self.assertTrue(noise_tracker.recording_complete())

    def test_all_loud_data(self):
        """Check that only loud samples doesn't generate a complete recording.
        """
        noise_tracker = NoiseTracker(MIN_NOISE, MAX_NOISE, SECS_PER_BUFFER,
                                     LOUD_TIME_LIMIT, SILENCE_TIME_LIMIT)

        num_high_updates = int(LOUD_TIME_LIMIT / SECS_PER_BUFFER) + 1
        for _ in range(num_high_updates):
            noise_tracker.update(True)
            self.assertFalse(noise_tracker.recording_complete())

    def test_all_loud_followed_by_silence(self):
        """Check that a long enough high sentence is completed after silence.
        """
        noise_tracker = NoiseTracker(MIN_NOISE, MAX_NOISE, SECS_PER_BUFFER,
                                     LOUD_TIME_LIMIT, SILENCE_TIME_LIMIT)

        num_high_updates = int(LOUD_TIME_LIMIT / SECS_PER_BUFFER) + 1
        for _ in range(num_high_updates):
            noise_tracker.update(True)
            self.assertFalse(noise_tracker.recording_complete())
        while not noise_tracker._quiet_enough():
            noise_tracker.update(False)
        self.assertTrue(noise_tracker.recording_complete())
