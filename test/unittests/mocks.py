from unittest.mock import Mock

from msm import MycroftSkillsManager
from msm.skill_repo import SkillRepo


def mock_msm(temp_dir):
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
    return dict(
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


class MessageBusMock:
    def __init__(self):
        self.message_types = []
        self.message_data = []
        self.event_handlers = []

    def emit(self, message):
        self.message_types.append(message.type)
        self.message_data.append(message.data)

    def on(self, event, _):
        self.event_handlers.append(event)
