"""Provide a common API for skills that define idle screen functionality."""
from datetime import datetime, timedelta

from mycroft.messagebus import Message
from .mycroft_skill import MycroftSkill


class IdleDisplaySkill(MycroftSkill):
    """Base class for skills that define an idle display.

    An idle display is what shows on a device's screen when it is not in use
    by other skills.  For example, Mycroft's Home Screen Skill.
    """
    def initialize(self):
        self._define_message_bus_handlers()

    def _define_message_bus_handlers(self):
        """Defines the bus events handled in this skill and their handlers."""
        self.bus.on("mycroft.ready", self.handle_mycroft_ready)
        self.bus.on("mycroft.gui.screen.close", self.handle_screen_close)
        self.bus.on("gui.page.show", self.handle_gui_page_show)
        self.bus.on("mycroft.skills.loaded", self.handle_skill_loaded)

    def handle_mycroft_ready(self, _):
        """Executes code dependent on the "mycroft.ready" event."""
        self._show_idle_screen()

    def _show_idle_screen(self):
        """Override this method with logic to display the idle screen."""
        raise NotImplementedError(
            "Subclass must override the _show_idle_screen method"
        )

    def handle_screen_close(self, _):
        """Executes code dependent on the "mycroft.gui.screen.close" event.

        Some skills have screens that show indefinitely. These screens should
        use the "mycroft.gui.screen.close" event to indicate indicate they
        are releasing the display for the idle screen.
        """
        self._show_idle_screen()

    def handle_gui_page_show(self, message: Message):
        """Executes code dependent on the "gui.page.show" event.

        Args:
            message: Message sent over the bus to show a page on the display
        """
        self._schedule_page_expiration(message)

    def _schedule_page_expiration(self, message: Message):
        """Schedules an event to show the idle screen.

        Skills with GUI components can dictate how long screens it sends to
        the display are shown.  If a duration is not specified, a default of
        15 seconds is used.  Some skills have screens that show indefinitely.
        These screens should use the "mycroft.gui.screen.close" event to
        reactivate the idle screen.

        Args:
            message: Message sent over the bus to show a page on the display
        """
        skill_id = message.data["__from"]
        if skill_id != self.skill_id:
            self.cancel_scheduled_event("ShowIdle")
            expiration_time = self._determine_expiration_time(message)
            if expiration_time is not None:
                self.schedule_event(
                    self._show_idle_screen,
                    when=expiration_time,
                    name="ShowIdle"
                )

    def _determine_expiration_time(self, message):
        """Determine the time the page showing on the screen expires."""
        page_duration = None
        expiration_time = None
        if type(message.data["__idle"]) == int:
            page_duration = message.data["__idle"]
        elif message.data["__idle"] is None:
            page_duration = 15
        if page_duration is not None:
            expiration_time = datetime.now() + timedelta(seconds=page_duration)
            self.log.info(
                f"Display returning to idle state in {page_duration} seconds"
            )

        return expiration_time

    def handle_skill_loaded(self, message):
        """Executes code dependent on the "mycroft.skills.loaded" event.

         Args:
             message: Message sent over the bus to indicate a skill has loaded
         """
        if message.data["id"] == self.skill_id:
            self._show_idle_screen()
