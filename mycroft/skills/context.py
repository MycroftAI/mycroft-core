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
from functools import wraps

"""
Helper decorators for handling context from skills.
"""


def adds_context(context, words=''):
    """Decorator adding context to the Adapt context manager.

    Args:
        context (str): context Keyword to insert
        words (str): optional string content of Keyword
    """

    def context_add_decorator(func):
        @wraps(func)
        def func_wrapper(*args, **kwargs):
            ret = func(*args, **kwargs)
            args[0].set_context(context, words)
            return ret

        return func_wrapper

    return context_add_decorator


def removes_context(context):
    """Decorator removing context from the Adapt context manager.

    Args:
        context (str): Context keyword to remove
    """

    def context_removes_decorator(func):
        @wraps(func)
        def func_wrapper(*args, **kwargs):
            ret = func(*args, **kwargs)
            args[0].remove_context(context)
            return ret

        return func_wrapper

    return context_removes_decorator
