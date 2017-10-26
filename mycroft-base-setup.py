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
from setuptools import setup

from mycroft.util.setup_base import (
    find_all_packages,
    required,
    get_version,
    place_manifest
)

place_manifest('mycroft-base-MANIFEST.in')

setup(
    name="mycroft-core",
    version=get_version(),
    install_requires=[required('requirements.txt')],
    packages=find_all_packages("mycroft"),
    include_package_data=True,

    entry_points={
        'console_scripts': [
            'mycroft-speech-client=mycroft.client.speech.main:main',
            'mycroft-messagebus=mycroft.messagebus.service.main:main',
            'mycroft-skills=mycroft.skills.main:main',
            'mycroft-audio=mycroft.audio.main:main',
            'mycroft-echo-observer=mycroft.messagebus.client.ws:echo',
            'mycroft-audio-test=mycroft.util.audio_test:main',
            'mycroft-enclosure-client=mycroft.client.enclosure.main:main',
            'mycroft-skill-container=mycroft.skills.container:main',
            'mycroft-cli-client=mycroft.client.text.main:main'
        ]
    }
)
