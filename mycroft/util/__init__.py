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
from .string_utils import get_http, remove_last_slash, camel_case_split
from .audio_utils import (play_audio_file, play_wav, play_ogg, play_mp3,
                          record, find_input_device)
from .file_utils import (resolve_resource_file, read_stripped_lines, read_dict,
                         create_file, ensure_directory_exists,
                         curate_cache, get_cache_directory)
from .network_utils import connected
from .process_utils import (reset_sigint_handler, create_daemon,
                            wait_for_exit_signal, create_echo_function)
from .log import LOG
from .parse import extract_datetime, extract_number, normalize
from .signal import check_for_signal, create_signal, get_ipc_directory
from .platform import get_arch


def is_speaking():
    """Determine if Text to Speech is occurring

    Returns:
        bool: True while still speaking
    """
    LOG.info("mycroft.utils.is_speaking() is depreciated, use "
             "mycroft.audio.is_speaking() instead.")
    return mycroft.audio.is_speaking()


def wait_while_speaking():
    """Pause as long as Text to Speech is still happening

    Pause while Text to Speech is still happening.  This always pauses
    briefly to ensure that any preceeding request to speak has time to
    begin.
    """
    LOG.info("mycroft.utils.wait_while_speaking() is depreciated, use "
             "mycroft.audio.wait_while_speaking() instead.")
    return mycroft.audio.wait_while_speaking()


def stop_speaking():
    # TODO: Less hacky approach to this once Audio Manager is implemented
    # Skills should only be able to stop speech they've initiated
    LOG.info("mycroft.utils.stop_speaking() is depreciated, use "
             "mycroft.audio.stop_speaking() instead.")
    mycroft.audio.stop_speaking()
