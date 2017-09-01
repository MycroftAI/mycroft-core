from setuptools import setup

from mycroft.util.setup_base import get_version, place_manifest

__author__ = 'seanfitz'

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
