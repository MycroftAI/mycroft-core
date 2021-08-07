"""Functions related to manipulating the skills.json file."""
import json
from logging import getLogger
from os.path import expanduser, isfile, dirname
from os import makedirs

LOG = getLogger(__name__)
SKILL_STATE_PATH = '~/.mycroft/skills.json'


def load_device_skill_state() -> dict:
    """Contains info on how skills should be updated"""
    skills_data_path = expanduser(SKILL_STATE_PATH)
    device_skill_state = {}
    if isfile(skills_data_path):
        try:
            with open(skills_data_path) as skill_state_file:
                device_skill_state = json.load(skill_state_file)
        except json.JSONDecodeError:
            LOG.exception('failed to load skills.json')

    return device_skill_state


def write_device_skill_state(data: dict):
    """Write the device skill state to disk."""
    dir_path = dirname(expanduser(SKILL_STATE_PATH))
    try:
        # create folder if it does not exist
        makedirs(dir_path)
    except Exception:
        pass
    skill_state_path = expanduser(SKILL_STATE_PATH)
    with open(skill_state_path, 'w') as skill_state_file:
        json.dump(data, skill_state_file, indent=4, separators=(',', ':'))


def get_skill_state(name, device_skill_state) -> dict:
    """Find a skill entry in the device skill state and returns it."""
    skill_state_return = {}
    for skill_state in device_skill_state.get('skills', []):
        if skill_state.get('name') == name:
            skill_state_return = skill_state

    return skill_state_return


def initialize_skill_state(name, origin, beta, skill_gid) -> dict:
    """Create a new skill entry
    
    Arguments:
        name: skill name
        origin: the source of the installation
        beta: Boolean indicating wether the skill is in beta
        skill_gid: skill global id
    Returns:
        populated skills entry
    """
    return dict(
        name=name,
        origin=origin,
        beta=beta,
        status='active',
        installed=0,
        updated=0,
        installation='installed',
        skill_gid=skill_gid
    )


def device_skill_state_hash(data):
    return hash(json.dumps(data, sort_keys=True))
