# Copyright (c) 2018 Mycroft AI, Inc.
#
# This file is part of Mycroft Skills Kit
# (see https://github.com/MycroftAI/mycroft-skills-kit).
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
from functools import wraps


def unset():
    raise NotImplementedError


class Lazy:
    """Lazy attribute across all instances"""
    initial_val = []

    def __init__(self, func):
        wraps(func)(self)
        self.func = func
        self.return_val = self.initial_val

    def __set__(self, instance, value):
        self.return_val = value

    def __get__(self, instance, owner):
        if self.return_val is self.initial_val:
            self.return_val = self.func(instance)
        return self.return_val
