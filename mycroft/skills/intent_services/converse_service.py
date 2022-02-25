import time

from mycroft.configuration import Configuration
from mycroft.messagebus.message import Message
from mycroft.skills.intent_services import (
    IntentMatch
)
from mycroft.skills.permissions import ConverseMode, ConverseActivationMode
from mycroft.util.log import LOG


class ConverseService:
    """Intent Service handling conversational skills."""

    def __init__(self, bus):
        self.bus = bus
        self._consecutive_activations = {}
        self.active_skills = []  # [skill_id , timestamp]

    @property
    def config(self):
        """
        Returns:
            converse_config (dict): config for converse handling options
        """
        return Configuration.get().get("skills", {}).get("converse") or {}

    def get_active_skills(self):
        """Active skill ids ordered by converse priority
        this represents the order in which converse will be called

        Returns:
            active_skills (list): ordered list of skill_ids
        """
        return [skill[0] for skill in self.active_skills]

    def deactivate_skill(self, skill_id, source_skill=None):
        """Remove a skill from being targetable by converse.

        Args:
            skill_id (str): skill to remove
            source_skill (str): skill requesting the removal
        """
        source_skill = source_skill or skill_id
        if self._deactivate_allowed(skill_id, source_skill):
            active_skills = self.get_active_skills()
            if skill_id in active_skills:
                idx = active_skills.index(skill_id)
                self.active_skills.pop(idx)
                self.bus.emit(
                    Message("intent.service.skills.deactivated",
                            {"skill_id": skill_id}))
                if skill_id in self._consecutive_activations:
                    self._consecutive_activations[skill_id] = 0

    def activate_skill(self, skill_id, source_skill=None):
        """Add a skill or update the position of an active skill.

        The skill is added to the front of the list, if it's already in the
        list it's removed so there is only a single entry of it.

        Args:
            skill_id (str): identifier of skill to be added.
            source_skill (str): skill requesting the removal
        """
        source_skill = source_skill or skill_id
        if self._activate_allowed(skill_id, source_skill):
            # NOTE: do not call self.remove_active_skill
            # do not want to send the deactivation bus event!
            active_skills = self.get_active_skills()
            if skill_id in active_skills:
                idx = active_skills.index(skill_id)
                self.active_skills.pop(idx)

            # add skill with timestamp to start of skill_list
            self.active_skills.insert(0, [skill_id, time.time()])
            self.bus.emit(
                Message("intent.service.skills.activated",
                        {"skill_id": skill_id}))

            self._consecutive_activations[skill_id] += 1

    def _activate_allowed(self, skill_id, source_skill=None):
        """Checks if a skill_id is allowed to jump to the front of active skills list

        - can a skill activate a different skill
        - is the skill blacklisted from conversing
        - is converse configured to only allow specific skills
        - did the skill activate too many times in a row

        Args:
            skill_id (str): identifier of skill to be added.
            source_skill (str): skill requesting the removal

        Returns:
            permitted (bool): True if skill can be activated
        """

        # cross activation control if skills can activate each other
        if not self.config.get("cross_activation"):
            source_skill = source_skill or skill_id
            if skill_id != source_skill:
                # different skill is trying to activate this skill
                return False

        # mode of activation dictates under what conditions a skill is
        # allowed to activate itself
        acmode = self.config.get("converse_activation") or \
                 ConverseActivationMode.ACCEPT_ALL
        if acmode == ConverseActivationMode.PRIORITY:
            prio = self.config.get("converse_priorities") or {}
            # only allowed to activate if no skill with higher priority is
            # active, currently there is no api for skills to
            # define their default priority, this is a user/developer setting
            priority = prio.get(skill_id, 50)
            if any(p > priority for p in
                   [prio.get(s[0], 50) for s in self.active_skills]):
                return False
        elif acmode == ConverseActivationMode.BLACKLIST:
            if skill_id in self.config.get("converse_blacklist", []):
                return False
        elif acmode == ConverseActivationMode.WHITELIST:
            if skill_id not in self.config.get("converse_whitelist", []):
                return False

        # limit of consecutive activations
        default_max = self.config.get("max_activations", -1)
        # per skill override limit of consecutive activations
        skill_max = self.config.get("skill_activations", {}).get(skill_id)
        max_activations = skill_max or default_max
        if skill_id not in self._consecutive_activations:
            self._consecutive_activations[skill_id] = 0
        if max_activations < 0:
            pass  # no limit (mycroft-core default)
        elif max_activations == 0:
            return False  # skill activation disabled
        elif self._consecutive_activations.get(skill_id, 0) > max_activations:
            return False  # skill exceeded authorized consecutive number of activations
        return True

    def _deactivate_allowed(self, skill_id, source_skill=None):
        """Checks if a skill_id is allowed to be removed from active skills list

        - can a skill deactivate a different skill

        Args:
            skill_id (str): identifier of skill to be added.
            source_skill (str): skill requesting the removal

        Returns:
            permitted (bool): True if skill can be deactivated
        """
        # cross activation control if skills can deactivate each other
        if not self.config.get("cross_activation"):
            source_skill = source_skill or skill_id
            if skill_id != source_skill:
                # different skill is trying to deactivate this skill
                return False
        return True

    def _converse_allowed(self, skill_id):
        """Checks if a skill_id is allowed to converse

        - is the skill blacklisted from conversing
        - is converse configured to only allow specific skills

        Args:
            skill_id (str): identifier of skill that wants to converse.

        Returns:
            permitted (bool): True if skill can converse
        """
        opmode = self.config.get("converse_mode",
                                 ConverseMode.ACCEPT_ALL)
        if opmode == ConverseMode.BLACKLIST and skill_id in \
                self.config.get("converse_blacklist", []):
            return False
        elif opmode == ConverseMode.WHITELIST and skill_id not in \
                self.config.get("converse_whitelist", []):
            return False
        return True

    def _collect_converse_skills(self):
        """use the messagebus api to determine which skills want to converse
        This includes all skills and external applications"""
        skill_ids = []
        want_converse = []
        active_skills = self.get_active_skills()

        def handle_ack(message):
            skill_id = message.data["skill_id"]
            if message.data.get("can_handle", True):
                if skill_id in active_skills:
                    want_converse.append(skill_id)
            skill_ids.append(skill_id)

        self.bus.on("skill.converse.pong", handle_ack)

        # wait for all skills to acknowledge they want to converse
        self.bus.emit(Message("skill.converse.ping"))
        start = time.time()
        while not all(s in skill_ids for s in active_skills) \
                and time.time() - start <= 0.5:
            time.sleep(0.02)

        self.bus.remove("skill.converse.pong", handle_ack)
        return want_converse

    def _check_converse_timeout(self):
        """ filter active skill list based on timestamps """
        timeouts = self.config.get("skill_timeouts") or {}
        def_timeout = self.config.get("timeout", 300)
        self.active_skills = [
            skill for skill in self.active_skills
            if time.time() - skill[1] <= timeouts.get(skill[0], def_timeout)]

    def converse(self, utterances, skill_id, lang, message):
        """Call skill and ask if they want to process the utterance.

        Args:
            utterances (list of tuples): utterances paired with normalized
                                         versions.
            skill_id: skill to query.
            lang (str): current language
            message (Message): message containing interaction info.

        Returns:
            handled (bool): True if handled otherwise False.
        """
        if self._converse_allowed(skill_id):
            converse_msg = message.reply("skill.converse.request",
                                         {"skill_id": skill_id,
                                          "utterances": utterances,
                                          "lang": lang})
            result = self.bus.wait_for_response(converse_msg,
                                                'skill.converse.response')
            if result and 'error' in result.data:
                error_msg = result.data['error']
                LOG.error(f"{skill_id}: {error_msg}")
                return False
            elif result is not None:
                return result.data.get('result', False)
        return False

    def converse_with_skills(self, utterances, lang, message):
        """Give active skills a chance at the utterance

        Args:
            utterances (list):  list of utterances
            lang (string):      4 letter ISO language code
            message (Message):  message to use to generate reply

        Returns:
            IntentMatch if handled otherwise None.
        """
        utterances = [item for tup in utterances or [] for item in tup]
        # filter allowed skills
        self._check_converse_timeout()
        # check if any skill wants to handle utterance
        for skill_id in self._collect_converse_skills():
            if self.converse(utterances, skill_id, lang, message):
                return IntentMatch('Converse', None, None, skill_id)
        return None

