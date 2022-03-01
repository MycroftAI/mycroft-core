from mycroft.messagebus import Message
from mycroft.configuration import Configuration, LocalConf, USER_CONFIG
from mycroft.util.log import LOG
from .namespace import NamespaceManager


class HomescreenManager:

    def __init__(self, bus, gui):
        self.bus = bus
        self.gui = gui
        self.homescreens = []
        self.mycroft_ready = False
        self.bus.on('homescreen.manager.add', self.add_homescreen)
        self.bus.on('homescreen.manager.remove', self.remove_homescreen)
        self.bus.on('homescreen.manager.list', self.get_homescreens)
        self.bus.on("homescreen.manager.get_active",
                    self.get_active_homescreen)
        self.bus.on("homescreen.manager.set_active",
                    self.set_active_homescreen)
        self.bus.on("homescreen.manager.disable_active",
                    self.disable_active_homescreen)
        self.bus.on("mycroft.mark2.register_idle",
                    self.register_old_style_homescreen)
        self.bus.on("homescreen.manager.show_active", self.show_homescreen)
        self.bus.on("mycroft.ready", self.set_mycroft_ready)

    def run(self):
        """Start the Manager after it has been constructed."""
        self.reload_homescreens_list()

    def add_homescreen(self, homescreen):
        # if homescreen[id] not in self.homescreens then add it
        homescreen_id = homescreen.data["id"]
        homescreen_class = homescreen.data["class"]
        LOG.info(f"Homescreen Manager: Adding Homescreen {homescreen_id}")
        # check if the list is empty
        if len(self.homescreens) == 0:
            self.homescreens.append(homescreen.data)
        else:
            # check if id is in list of homescreen dicts in self.homescreens
            for h in self.homescreens:
                if homescreen_id != h["id"]:
                    self.homescreens.append(homescreen.data)

        self.show_homescreen_on_add(homescreen_id, homescreen_class)

    def remove_homescreen(self, homescreen):
        homescreen_id = homescreen.data["id"]
        LOG.info(f"Homescreen Manager: Removing Homescreen {homescreen_id}")
        for h in self.homescreens:
            if homescreen_id == h["id"]:
                self.homescreens.pop(h)

    def get_homescreens(self):
        return self.homescreens

    def get_active_homescreen(self):
        config = Configuration.get()
        enclosure_config = config.get("gui")
        active_homescreen = enclosure_config.get("idle_display_skill")
        LOG.debug(f"Homescreen Manager: Active Homescreen {active_homescreen}")
        for h in self.homescreens:
            if h["id"] == active_homescreen:
                return active_homescreen

    def set_active_homescreen(self, homescreen):
        homescreen_id = homescreen.data["id"]
        conf = LocalConf(USER_CONFIG)
        conf["gui"] = {
            "idle_display_skill": homescreen_id,
        }
        conf.store()
        self.bus.emit(Message("configuration.patch", {"config": conf}))

    def reload_homescreens_list(self):
        LOG.info("Homescreen Manager: Reloading Homescreen List")
        self.collect_old_style_homescreens()
        self.bus.emit(Message("homescreen.manager.reload.list"))

    def show_homescreen_on_add(self, homescreen_id, homescreen_class):
        if self.mycroft_ready == True:
            active_homescreen = self.get_active_homescreen()
            if active_homescreen == homescreen_id:
                if homescreen_class == "IdleDisplaySkill":
                    LOG.debug(
                        f"Homescreen Manager: Displaying Homescreen {active_homescreen}")
                    self.bus.emit(Message("homescreen.manager.activate.display", {
                                  "homescreen_id": active_homescreen}))
                elif homescreen_class == "MycroftSkill":
                    LOG.debug(
                        f"Homescreen Manager: Displaying Homescreen {active_homescreen}")
                    self.bus.emit(Message("{}.idle".format(homescreen_id)))

    def disable_active_homescreen(self, message):
        conf = LocalConf(USER_CONFIG)
        conf["gui"] = {
            "idle_display_skill": None,
        }
        conf.store()
        self.bus.emit(Message("configuration.patch", {"config": conf}))

    def show_homescreen(self, message=None):
        active_homescreen = self.get_active_homescreen()
        for h in self.homescreens:
            if h["id"] == active_homescreen:
                if h["class"] == "IdleDisplaySkill":
                    LOG.debug(
                        f"Homescreen Manager: Displaying Homescreen {active_homescreen}")
                    self.bus.emit(Message("homescreen.manager.activate.display", {
                                  "homescreen_id": active_homescreen}))
                elif h["class"] == "MycroftSkill":
                    LOG.debug(
                        f"Homescreen Manager: Displaying Homescreen {active_homescreen}")
                    self.bus.emit(Message("{}.idle".format(active_homescreen)))

    def set_mycroft_ready(self, message):
        self.mycroft_ready = True
        self.show_homescreen()

    # Add compabitility with older versions of the Resting Screen Class

    def collect_old_style_homescreens(self):
        """Trigger collection of older resting screens."""
        self.bus.emit(Message("mycroft.mark2.collect_idle"))

    def register_old_style_homescreen(self, message):
        if "name" in message.data and "id" in message.data:
            super_class_name = "MycroftSkill"
            super_class_object = message.data["name"]
            skill_id = message.data["id"]
            _homescreen_entry = {"class": super_class_name,
                                 "name": super_class_object, "id": skill_id}
            LOG.debug("Homescreen Manager: Adding OLD Homescreen {skill_id}")
            self.add_homescreen(
                Message("homescreen.manager.add", _homescreen_entry))
        else:
            LOG.error("Malformed idle screen registration received")
