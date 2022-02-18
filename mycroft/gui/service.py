from mycroft.messagebus import Message
from mycroft.messagebus.client import MessageBusClient
from mycroft.util import create_daemon, start_message_bus_client
from mycroft.configuration import Configuration, LocalConf, USER_CONFIG
from mycroft.util.log import LOG
from .namespace import NamespaceManager

class GUIService:
    def __init__(self):
        self.bus = MessageBusClient()
        self.gui = NamespaceManager(self.bus)

        self.homescreens = []
        self.bus.on('homescreen.manager.add', self.add_homescreen)
        self.bus.on('homescreen.manager.remove', self.remove_homescreen)
        self.bus.on('homescreen.manager.list', self.get_homescreens)
        self.bus.on("homescreen.manager.get_active", self.get_active_homescreen)
        self.bus.on("homescreen.manager.set_active", self.set_active_homescreen)
        self.bus.on("homescreen.manager.disable_active", self.disable_active_homescreen)

    def run(self):
        """Start the GUI after it has been constructed."""
        # Allow exceptions to be raised to the GUI Service
        # if they may cause the Service to fail.
        start_message_bus_client("GUI_SERVICE", self.bus)
        self.reload_homescreens_list()

    def add_homescreen(self, homescreen):
        # if homescreen[id] not in self.homescreens then add it
        homescreen_id = homescreen.data["id"]
        LOG.info("Homescreen Manager: Adding Homescreen {}".format(homescreen_id))
        # check if the list is empty
        if len(self.homescreens) == 0:
            self.homescreens.append(homescreen.data)
        else:
            # check if id is in list of homescreen dicts in self.homescreens
            for h in self.homescreens:
                if homescreen_id != h["id"]:
                    self.homescreens.append(homescreen.data)
    
        self.show_homescreen_on_add(homescreen_id)

    def remove_homescreen(self, homescreen):
        homescreen_id = homescreen.data["id"]
        LOG.info("Homescreen Manager: Removing Homescreen {}".format(homescreen_id))
        for h in self.homescreens:
            if homescreen_id == h["id"]:
                self.homescreens.pop(h)

    def get_homescreens(self):
        return self.homescreens

    def get_active_homescreen(self):
        config = Configuration.get()
        enclosure_config = config.get("enclosure")
        active_homescreen = enclosure_config.get("idle_display_skill")
        LOG.debug("Homescreen Manager: Active Homescreen {}".format(active_homescreen))
        for h in self.homescreens:
            if h["id"] == active_homescreen:
                return active_homescreen

    def set_active_homescreen(self, homescreen):
        homescreen_id = homescreen.data["id"]
        conf = LocalConf(USER_CONFIG)
        conf["enclosure"] = {
            "idle_display_skill": homescreen_id,
        }
        conf.store()
        self.bus.emit(Message("configuration.patch", {"config": conf}))

    def reload_homescreens_list(self):
        LOG.info("Homescreen Manager: Reloading Homescreen List")
        self.bus.emit(Message("homescreen.manager.reload.list"))

    def show_homescreen_on_add(self, homescreen_id):
        active_homescreen = self.get_active_homescreen()
        if active_homescreen == homescreen_id:
            LOG.info("Homescreen Manager: Displaying Homescreen {}".format(active_homescreen))
            self.bus.emit(Message("homescreen.manager.activate.display", {"homescreen_id": active_homescreen}))
    
    def disable_active_homescreen(self, message):
        conf = LocalConf(USER_CONFIG)
        conf["enclosure"] = {
            "idle_display_skill": None,
        }
        conf.store()
        self.bus.emit(Message("configuration.patch", {"config": conf}))

    def stop(self):
        """Perform any GUI shutdown processes."""
        pass
