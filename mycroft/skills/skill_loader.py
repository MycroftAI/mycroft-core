import gc
import os
import sys
from time import time


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
    def __init__(self, bus, skill_directory):
        self.bus = bus
        self.skill_directory = skill_directory
        self.skill_id = os.path.basename(skill_directory)
        self.load_attempted = False
        self.loaded = False
        self.last_modified = 0
        self.last_loaded = 0
        self.instance = None
        self.active = True

    @property
    def config(self):
        return Configuration.get()

    def load(self):
        """Reload unloaded/changed needs if necessary.

        Returns:
             bool: if the skill was loaded/reloaded
        """
        self.last_modified = _get_last_modified_date(self.skill_directory)
        modified = self.last_modified > self.last_loaded
        reload_allowed = self.active and self.instance.reload_skill
        if self.loaded and modified and reload_allowed:
            LOG.debug('Attempting to reload skill in ' + self.skill_directory)
            if reload_allowed:
                LOG.debug('Shutting down skill in ' + self.skill_directory)
                self._shutdown()
            else:
                log_msg = 'Reloading blocked for skill in {} - aborting.'
                LOG.debug(log_msg.format(self.skill_directory))

        if not self.loaded or (self.loaded and modified and reload_allowed):
            self.load_attempted = True
            LOG.debug('Loading skill in ' + self.skill_directory)
            self._load_skill()
            self._communicate_load_status()

    def _shutdown(self):
        """Remove listeners and stop threads before loading"""
        try:
            self.instance.default_shutdown()
        except Exception as e:
            log_msg = 'An error occurred while shutting down {}'
            LOG.error(log_msg.format(self.instance.name))
            LOG.exception(e)

        if self.config.get("debug", False):
            gc.collect()  # Collect garbage to remove false references
            # Remove two local references that are known
            refs = sys.getrefcount(self.instance) - 2
            if refs > 0:
                log_msg = (
                    "After shutdown of {} there are still {} references "
                    "remaining. The skill won't be cleaned from memory."
                )
                LOG.warning(log_msg.format(self.instance.name, refs))
        message = Message(
            "mycroft.skills.shutdown",
            data=dict(path=self.skill_directory, id=self.skill_id)
        )
        self.bus.emit(message)

    def _load_skill(self):
        self.loaded = False
        descriptor = create_skill_descriptor(self.skill_directory)
        blacklisted = self.config['skills'].get('blacklisted_skills', [])
        self.instance = load_skill(
            descriptor,
            self.bus,
            self.skill_id,
            blacklisted
        )
        if self.instance is not None:
            self.loaded = True
            self.last_loaded = time()

    def _communicate_load_status(self):
        if self.loaded:
            message = Message(
                'mycroft.skills.loaded',
                data=dict(
                    path=self.skill_directory,
                    id=self.skill_id,
                    name=self.instance.name,
                    modified=self.last_modified
                )
            )
            self.bus.emit(message)
            self.skill_was_loaded = True
        else:
            message = Message(
                'mycroft.skills.loading_failure',
                data=dict(path=self.skill_directory, id=self.skill_id)
            )
            self.bus.emit(message)
