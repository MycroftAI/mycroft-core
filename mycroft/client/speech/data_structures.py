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
"""Data structures used by the speech client."""


class RollingMean:
    """Simple rolling mean calculation optimized for speed.

    The optimization is made for cases where value retrieval is made at a
    comparative rate to the sample additions.

    Arguments:
        mean_samples: Number of samples to use for mean value
    """
    def __init__(self, mean_samples):
        self.num_samples = mean_samples
        self.samples = []
        self.value = None  # Leave unintialized
        self.replace_pos = 0  # Position to replace

    def append_sample(self, sample):
        """Add a sample to the buffer.

        The sample will be appended if there is room in the buffer,
        otherwise it will replace the oldest sample in the buffer.
        """
        sample = float(sample)
        current_len = len(self.samples)
        if current_len < self.num_samples:
            # build the mean
            self.samples.append(sample)
            if self.value is not None:
                avgsum = self.value * current_len + sample
                self.value = avgsum / (current_len + 1)
            else:  # If no samples are in the buffer set the sample as mean
                self.value = sample
        else:
            # Remove the contribution of the old sample
            replace_val = self.samples[self.replace_pos]
            self.value -= replace_val / self.num_samples

            # Replace it with the new sample and update the mean with it's
            # contribution
            self.value += sample / self.num_samples
            self.samples[self.replace_pos] = sample

            # Update replace position
            self.replace_pos = (self.replace_pos + 1) % self.num_samples


class CyclicAudioBuffer:
    """A Cyclic audio buffer for storing binary data.

    TODO: The class is still unoptimized and performance can probably be
    enhanced.

    Arguments:
        size (int): size in bytes
        initial_data (bytes): initial buffer data
    """
    def __init__(self, size, initial_data):
        self.size = size
        # Get at most size bytes from the end of the initial data
        self._buffer = initial_data[-size:]

    def append(self, data):
        """Add new data to the buffer, and slide out data if the buffer is full

        Arguments:
            data (bytes): binary data to append to the buffer. If buffer size
                          is exceeded the oldest data will be dropped.
        """
        buff = self._buffer + data
        if len(buff) > self.size:
            buff = buff[-self.size:]
        self._buffer = buff

    def get(self):
        """Get the binary data."""
        return self._buffer

    def get_last(self, size):
        """Get the last entries of the buffer."""
        return self._buffer[-size:]

    def __getitem__(self, key):
        return self._buffer[key]

    def __len__(self):
        return len(self._buffer)
