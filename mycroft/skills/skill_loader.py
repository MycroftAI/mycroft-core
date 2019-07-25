import gc
import os
import sys


from mycroft.configuration import Configuration
from mycroft.messagebus import Message
from mycroft.util.log import LOG
from .core import create_skill_descriptor, load_skill


def _get_last_modified_date(path):
    """Get the last modified date of the most recently updated file in a path.

    Exclude compiled python files, hidden directories and the settings.json
    file.

    Arguments:
        path: skill directory to check

    Returns:
        int: time of last change
    """
    all_files = []
    for root_dir, dirs, files in os.walk(path):
        dirs[:] = [d for d in dirs if not d.startswith('.')]
        for f in files:
            ignore_file = (
                    f.endswith('.pyc') or
                    f == 'settings.json' or
                    f.startswith('.') or
                    f.endswith('.qmlc')
            )
            if not ignore_file:
                all_files.append(os.path.join(root_dir, f))

    # check files of interest in the skill root directory
    return max(os.path.getmtime(f) for f in all_files)


class SkillLoader:
    def __init__(self, bus, skill_directory, skill):
        self.bus = bus
        self.skill_directory = skill_directory
        self.skill = dict(**skill)
        self.skill.update(
            id=os.path.basename(skill_directory),
            path=skill_directory,
            loaded=False if 'loaded' not in skill else skill['loaded']
        )
        self.directory_last_modified = _get_last_modified_date(skill_directory)
        self.skill_was_loaded = False

    @property
    def config(self):
        return Configuration.get()

    @property
    def do_load(self):
        loaded = self.skill['loaded']
        skill_instance = self.skill.get('instance')

        return not loaded or skill_instance is None

    @property
    def do_reload(self):
        is_loaded = self.skill['loaded']
        skill_last_modified = self.skill.get('last_modified', 0)
        is_modified = self.directory_last_modified > skill_last_modified
        skill_instance = self.skill.get('instance')

        return is_loaded and is_modified and skill_instance is not None

    @property
    def reload_blocked(self):
        skill_instance = self.skill.get('instance')
        active = self.skill.get('active', True)

        return (
            self.do_reload and
            not active and
            not skill_instance.reload_skill
        )

    def load(self):
        """Reload unloaded/changed needs if necessary.

        Returns:
             bool: if the skill was loaded/reloaded
        """
        if self.do_reload and not self.reload_blocked:
            LOG.debug('Attempting to reload skill in ' + self.skill_directory)
            if self.reload_blocked:
                log_msg = 'Reloading blocked for skill in {} - aborting.'
                LOG.debug(log_msg.format(self.skill_directory))
            else:
                LOG.debug('Shutting down skill in ' + self.skill_directory)
                self._shutdown()

        if self.do_load or (self.do_reload and not self.reload_blocked):
            LOG.debug('Loading skill in ' + self.skill_directory)
            self._load_skill()
            self._communicate_load_status()

    def _shutdown(self):
        """Remove listeners and stop threads before loading"""
        instance = self.skill['instance']
        try:
            instance.default_shutdown()
        except Exception as e:
            log_msg = 'An error occurred while shutting down {}'
            LOG.error(log_msg.format(instance.name))
            LOG.exception(e)

        if self.config.get("debug", False):
            gc.collect()  # Collect garbage to remove false references
            # Remove two local references that are known
            refs = sys.getrefcount(instance) - 2
            if refs > 0:
                log_msg = (
                    "After shutdown of {} there are still {} references "
                    "remaining. The skill won't be cleaned from memory."
                )
                LOG.warning(log_msg.format(instance.name, refs))
        message = Message(
            "mycroft.skills.shutdown",
            data=dict(path=self.skill_directory, id=self.skill["id"])
        )
        self.bus.emit(message)

    def _load_skill(self):
        descriptor = create_skill_descriptor(self.skill_directory)
        blacklisted = self.config['skills'].get('blacklisted_skills', [])
        self.skill['instance'] = load_skill(
            descriptor,
            self.bus,
            self.skill['id'],
            blacklisted
        )
        if self.skill['instance'] is not None:
            self.skill['loaded'] = True
            self.skill['last_modified'] = self.directory_last_modified
        else:
            self.skill['loaded'] = False

    def _communicate_load_status(self):
        if self.skill['loaded']:
            message = Message(
                'mycroft.skills.loaded',
                data=dict(
                    path=self.skill_directory,
                    id=self.skill['id'],
                    name=self.skill['instance'].name,
                    modified=self.directory_last_modified
                )
            )
            self.bus.emit(message)
            self.skill_was_loaded = True
        else:
            message = Message(
                'mycroft.skills.loading_failure',
                data=dict(path=self.skill_directory, id=self.skill['id'])
            )
            self.bus.emit(message)
