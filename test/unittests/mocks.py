from unittest.mock import Mock

from msm import MycroftSkillsManager
from msm.skill_repo import SkillRepo

from mycroft.messagebus import MessageBusClient


def mock_msm(temp_dir):
    """Mock the MycroftSkillsManager because it reaches out to the internet."""
    msm_mock = Mock(spec=MycroftSkillsManager)
    msm_mock.skills_dir = temp_dir
    msm_mock.platform = 'test_platform'
    msm_mock.lock = Mock()
    msm_mock.repo = Mock(spec=SkillRepo)
    msm_mock.repo.get_default_skill_names = Mock(return_value=[
        ('default', ['time', 'weather']),
        ('test_platform', ['test_skill'])
    ])
    msm_mock.skills_data = dict(
        skills=[
            dict(name='test_skill', beta=False)
        ]
    )
    skill = Mock()
    skill.is_local = True
    msm_mock.list_defaults.return_value = [skill]

    return msm_mock


def mock_config(temp_dir):
    """Supply a reliable return value for the Configuration.get() method."""
    get_config_mock = Mock()
    get_config_mock.return_value = dict(
        skills=dict(
            msm=dict(
                directory='skills',
                versioned=True,
                repo=dict(
                    cache='.skills-repo',
                    url='https://github.com/MycroftAI/mycroft-skills',
                    branch='19.02'
                )
            ),
            update_interval=1.0,
            auto_update=False,
            blacklisted_skills=[],
            priority_skills=['foobar'],
            upload_skill_manifest=True
        ),
        data_dir=str(temp_dir)
    )

    return get_config_mock


class MessageBusMock:
    """Replaces actual message bus calls in unit tests.

    The message bus should not be running during unit tests so mock it
    out in a way that makes it easy to test code that calls it.
    """
    def __init__(self):
        self.message_types = []
        self.message_data = []
        self.event_handlers = []

    def emit(self, message):
        self.message_types.append(message.type)
        self.message_data.append(message.data)

    def on(self, event, _):
        self.event_handlers.append(event)
