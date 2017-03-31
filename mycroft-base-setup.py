from setuptools import setup

from mycroft.util.setup_base import (
    find_all_packages,
    required,
    get_version,
    place_manifest
)

__author__ = 'seanfitz'

place_manifest('mycroft-base-MANIFEST.in')

setup(
    name="mycroft-core",
    version=get_version(),
    install_requires=[required('requirements.txt'), 'wifi'],
    packages=find_all_packages("mycroft"),
    include_package_data=True,

    entry_points={
        'console_scripts': [
            'mycroft-speech-client=mycroft.client.speech.main:main',
            'mycroft-messagebus=mycroft.messagebus.service.main:main',
            'mycroft-skills=mycroft.skills.main:main',
            'mycroft-echo-observer=mycroft.messagebus.client.ws:echo',
            'mycroft-audio-test=mycroft.util.audio_test:main',
            'mycroft-enclosure-client=mycroft.client.enclosure.main:main',
            'mycroft-wifi-setup-client=mycroft.client.wifisetup.main:main',
            'mycroft-skill-container=mycroft.skills.container:main',
            'mycroft-cli-client=mycroft.client.text.main:main'
        ]
    }
)
