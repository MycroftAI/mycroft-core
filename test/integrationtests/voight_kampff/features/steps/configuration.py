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
import json
from os.path import join, exists
import time

from behave import given
from mycroft.messagebus import Message
from mycroft.util import resolve_resource_file

CONFIG_CHANGE_TIMEOUT = 10


def wait_for_config_change(context, key, expected_value):
    """Wait for a config change to apply.

    Waits until the specified key has changed into the expected value, if
    the change delays for too long a TimeoutError will be raised.

    Args:
        context (Context): Behave context of current scenario
        key (str): key to verify
        expected_value (Object): The expected value indicating that the change
                                 has been applied
    """
    start_time = time.monotonic()
    while context.config.get(key) != expected_value:
        time.sleep(0.5)
        if time.monotonic() - start_time >= CONFIG_CHANGE_TIMEOUT:
            raise TimeoutError


def reset_config(context):
    """Cleanup callback to reset patched configuration

    Args:
        context (Context): Behave context of current scenario
    """
    context.log.info('Resetting patched configuration...')
    context.bus.emit(Message('configuration.patch.clear'))
    key = list(context.original_config)[0]
    wait_for_config_change(context, key, context.original_config[key])


def patch_config(context, patch):
    """Apply patch to config and wait for it to take effect.

    Args:
        context: Behave context for test
        patch: patch to apply
    """
    context.log.info('Patching config with {}'.format(patch))
    # If this is first patch in scenario
    if not hasattr(context, 'original_config'):
        context.original_config = {}

    # store originals in context
    for key in patch:
        # If this patch is redefining an already changed key don't update
        if key not in context.original_config:
            context.original_config[key] = context.config.get(key)

    # Patch config
    patch_config_msg = Message('configuration.patch', {'config': patch})
    context.bus.emit(patch_config_msg)

    context.add_cleanup(reset_config, context)

    # Wait until one of the keys has been updated
    key = list(patch.keys())[0]
    wait_for_config_change(context, key, patch[key])


def get_config_file_definition(configs_path, config, value):
    """Read config definition file and return the matching patch dict.

    Args:
        configs_path: path to the configuration patch json file
        config: config value to fetch from the file
        value: predefined value to fetch

    Returns:
        Patch dictionary or None.
    """
    with open(configs_path) as f:
        configs = json.load(f)
        return configs.get(config, {}).get(value)


def get_global_config_definition(context, config, value):
    """Get config definitions included with Mycroft.

    Args:
        context: behave test context
        config: config value to fetch from the file
        value: predefined value to fetch

    Returns:
        Patch dictionary or None.
    """
    configs_path = resolve_resource_file(join('text', context.lang,
                                              'configurations.json'))
    return get_config_file_definition(configs_path, config, value)


def get_feature_config_definition(context, config, value):
    """Get config feature specific config defintion

    Args:
        context: behave test context
        config: config value to fetch from the file
        value: predefined value to fetch

    Returns:
        Patch dictionary or None.
    """
    feature_config = context.feature.filename.replace('.feature',
                                                      '.config.json')
    if exists(feature_config):
        return get_config_file_definition(feature_config, config, value)
    else:
        return None


@given('the user\'s {config} is {value}')
def given_config(context, config, value):
    """Patch the configuration with a specific config."""
    config = config.strip('"')
    value = value.strip('"')
    patch_dict = (get_feature_config_definition(context, config, value) or
                  get_global_config_definition(context, config, value))
    patch_config(context, patch_dict)
