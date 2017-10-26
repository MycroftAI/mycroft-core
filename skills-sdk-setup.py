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

from mycroft.util.setup_base import get_version, place_manifest


place_manifest("skills-sdk-MANIFEST.in")

setup(
    name="mycroft-skills-sdk",
    version=get_version(),
    install_requires=[
        "mustache==0.1.4",
        "configobj==5.0.6",
        "pyee==1.0.1",
        "adapt-parser==0.2.1",
        "padatious==0.1.4"
        "websocket-client==0.32.0"
    ],
    packages=[
        "mycroft.configuration",
        "mycroft.dialog",
        "mycroft.filesystem",
        "mycroft.messagebus",
        "mycroft.messagebus.client",
        "mycroft.session",
        "mycroft.skills",
        "mycroft.util",
        "mycroft"
    ],
    include_package_data=True,

    entry_points={
        'console_scripts': [
            'mycroft-skill-container=mycroft.skills.container:main'
        ]
    }
)
