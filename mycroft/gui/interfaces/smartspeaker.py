from mycroft.messagebus import Message
from ovos_utils.gui import GUIInterface


class SmartSpeakerExtensionGuiInterface(GUIInterface):
    def __init__(self, bus, homescreen_manager) -> None:
        super(SmartSpeakerExtensionGuiInterface, self).__init__(
            skill_id="SmartSpeakerExtension.GuiInterface")
        self.bus = bus
        self.homescreen_manager = homescreen_manager

        # Initiate Bind
        self.bind()

    def bind(self):
        super().set_bus(self.bus)

        self.bus.on("mycroft.device.settings", self.handle_device_settings)
        self.bus.on("ovos.PHAL.dashboard.status.response",
                    self.update_device_dashboard_status)
        self.register_handler("mycroft.device.settings",
                              self.handle_device_settings)
        self.register_handler(
            "mycroft.device.settings.homescreen", self.handle_device_homescreen_settings)
        self.register_handler("mycroft.device.settings.ssh",
                              self.handle_device_ssh_settings)
        self.register_handler(
            "mycroft.device.settings.developer",  self.handle_device_developer_settings)
        self.register_handler("mycroft.device.enable.dash",
                              self.handle_device_developer_enable_dash)
        self.register_handler("mycroft.device.disable.dash",
                              self.handle_device_developer_disable_dash)
        self.register_handler("mycroft.device.show.idle",
                              self.handle_show_homescreen)
        self.register_handler("mycroft.device.settings.customize",
                              self.handle_device_customize_settings)

    def handle_device_settings(self, message):
        """ Display device settings page. """
        self["state"] = "settings/settingspage"
        self.show_page("SYSTEM_AdditionalSettings.qml", override_idle=True)

    def handle_device_homescreen_settings(self, message):
        """
        display homescreen settings page
        """
        screens = self.homescreen_manager.homescreens
        self["idleScreenList"] = {"screenBlob": screens}
        self["selectedScreen"] = self.homescreen_manager.get_active_homescreen()
        self["state"] = "settings/homescreen_settings"
        self.show_page("SYSTEM_AdditionalSettings.qml", override_idle=True)

    def handle_device_ssh_settings(self, message):
        """
        display ssh settings page
        """
        self["state"] = "settings/ssh_settings"
        self.show_page("SYSTEM_AdditionalSettings.qml", override_idle=True)

    def handle_set_homescreen(self, message):
        """
        Set the homescreen to the selected screen
        """
        homescreen_id = message.data.get("homescreen_id", "")
        if homescreen_id:
            self.homescreen_manager.set_active_homescreen(homescreen_id)

    def handle_show_homescreen(self, message):
        self.homescreen_manager.show_homescreen()

    def handle_device_developer_settings(self, message):
        self['state'] = 'settings/developer_settings'
        self.handle_get_dash_status()

    def handle_device_developer_enable_dash(self, message):
        self.bus.emit(Message("ovos.PHAL.dashboard.enable"))

    def handle_device_developer_disable_dash(self, message):
        self.bus.emit(Message("ovos.PHAL.dashboard.disable"))

    def update_device_dashboard_status(self, message):
        call_check = message.data.get("status", False)
        dash_security_pass = message.data.get("password", "")
        dash_security_user = message.data.get("username", "")
        dash_url = message.data.get("url", "")
        if call_check:
            self["dashboard_enabled"] = call_check
            self["dashboard_url"] = dash_url
            self["dashboard_user"] = dash_security_user
            self["dashboard_password"] = dash_security_pass
        else:
            self["dashboard_enabled"] = call_check
            self["dashboard_url"] = ""
            self["dashboard_user"] = ""
            self["dashboard_password"] = ""

    def handle_device_customize_settings(self, message):
        self['state'] = 'settings/customize_settings'
        self.show_page("SYSTEM_AdditionalSettings.qml", override_idle=True)

    def handle_get_dash_status(self):
        self.bus.emit(Message("ovos.PHAL.dashboard.get.status"))
