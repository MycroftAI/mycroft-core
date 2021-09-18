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
"""Mycroft util library.

A collections of utils and tools for making skill development easier.
"""
from __future__ import absolute_import

import os

import mycroft.audio
from mycroft.util.format import nice_number
from .string_utils import camel_case_split
from .audio_utils import (play_audio_file, play_wav, play_ogg, play_mp3,
                          record, find_input_device, play_wav_sync, play_mp3_sync)
from .file_utils import (
    resolve_resource_file,
    read_stripped_lines,
    read_dict,
    create_file,
    get_temp_path,
    ensure_directory_exists,
    curate_cache,
    get_cache_directory)
from .network_utils import connected
from .process_utils import (reset_sigint_handler, create_daemon,
                            wait_for_exit_signal, create_echo_function,
                            start_message_bus_client)
from .log import LOG
from .parse import extract_datetime, extract_number, normalize
from .signal import check_for_signal, create_signal, get_ipc_directory
from .platform import get_arch
