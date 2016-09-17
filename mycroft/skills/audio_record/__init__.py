# Copyright 2016 Mycroft AI, Inc.
#
# This file is part of Mycroft Core.
#
# Mycroft Core is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Mycroft Core is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Mycroft Core.  If not, see <http://www.gnu.org/licenses/>.


import math
import time

import psutil as psutil
from adapt.intent import IntentBuilder
from os.path import dirname

from mycroft.skills.scheduled_skills import ScheduledSkill
from mycroft.util import record, play_wav
from mycroft.util.log import getLogger

__author__ = 'jdorleans'

LOGGER = getLogger(__name__)


class AudioRecordSkill(ScheduledSkill):
    def __init__(self):
        super(AudioRecordSkill, self).__init__("AudioRecordSkill")
        self.free_disk = self.config.get('free_disk')
        self.max_time = self.config.get('max_time')
        self.notify_delay = self.config.get('notify_delay')
        self.rate = self.config.get('rate')
        self.channels = self.config.get('channels')
        self.file_path = self.config.get('filename')
        self.duration = 0
        self.notify_time = None
        self.play_process = None
        self.record_process = None

    def initialize(self):
        self.load_data_files(dirname(__file__))

        intent = IntentBuilder("AudioRecordSkillIntent").require(
            "AudioRecordSkillKeyword").build()
        self.register_intent(intent, self.handle_record)

        intent = IntentBuilder('AudioRecordSkillStopIntent').require(
            'AudioRecordSkillStopVerb') \
            .require('AudioRecordSkillKeyword').build()
        self.register_intent(intent, self.handle_stop)

        intent = IntentBuilder('AudioRecordSkillPlayIntent').require(
            'AudioRecordSkillPlayVerb') \
            .require('AudioRecordSkillKeyword').build()
        self.register_intent(intent, self.handle_play)

        intent = IntentBuilder('AudioRecordSkillStopPlayIntent').require(
            'AudioRecordSkillStopVerb') \
            .require('AudioRecordSkillPlayVerb').require(
            'AudioRecordSkillKeyword').build()
        self.register_intent(intent, self.handle_stop_play)

    def handle_record(self, message):
        utterance = message.data.get('utterance')
        date = self.get_utc_time(utterance)
        now = self.get_utc_time()
        self.duration = self.get_duration(date, now)
        if self.is_free_disk_space():
            self.notify_time = now
            self.feedback_start()
            time.sleep(3)
            self.record_process = record(
                self.file_path, self.duration, self.rate, self.channels)
            self.schedule()
        else:
            self.speak_dialog("audio.record.disk.full")

    def get_duration(self, date, now):
        duration = math.ceil(date - now)
        if duration <= 0:
            duration = self.max_time
        return int(duration)

    def is_free_disk_space(self):
        space = self.duration * self.channels * self.rate / 1024 / 1024
        free_mb = psutil.disk_usage('/')[2] / 1024 / 1024
        if free_mb - space > self.free_disk:
            return True
        else:
            return False

    def feedback_start(self):
        if self.duration > 0:
            self.speak_dialog(
                'audio.record.start.duration', {'duration': self.duration})
        else:
            self.speak_dialog('audio.record.start')

    def handle_stop(self, message):
        self.speak_dialog('audio.record.stop')
        if self.record_process:
            self.stop_process(self.record_process)
            self.record_process = None
            self.cancel()

    @staticmethod
    def stop_process(process):
        if process.poll() is None:
            process.terminate()
            process.wait()

    def get_times(self):
        return [self.notify_time]

    def notify(self, timestamp):
        if self.record_process and self.record_process.poll() is None:
            if self.is_free_disk_space():
                LOGGER.info("Recording...")
                self.notify_time = self.get_utc_time() + self.notify_delay
                self.schedule()
            else:
                self.handle_stop(None)
                self.speak_dialog("audio.record.disk.full")
        else:
            self.handle_stop(None)

    def handle_play(self, message):
        self.play_process = play_wav(self.file_path)

    def handle_stop_play(self, message):
        self.speak_dialog('audio.record.stop.play')
        if self.play_process:
            self.stop()
            self.play_process = None

    def stop(self):
        if self.play_process:
            self.stop_process(self.play_process)
        if self.record_process:
            self.stop_process(self.record_process)


def create_skill():
    return AudioRecordSkill()
