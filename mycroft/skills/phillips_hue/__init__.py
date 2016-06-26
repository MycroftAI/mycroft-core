from adapt.intent import IntentBuilder
from mycroft.skills.core import MycroftSkill
from mycroft.util.log import getLogger
from os.path import dirname
from phue import Bridge
from phue import Group
from phue import PhueRegistrationException
import socket
import time

__author__ = 'ChristopherRogers1991'

LOGGER = getLogger(__name__)


class DeviceNotFoundException(Exception):
    pass


class PhillipsHueSkill(MycroftSkill):

    def __init__(self):
        super(PhillipsHueSkill, self).__init__(name="PhillipsHueSkill")
        self.brightness_step =\
            int(self.config.get('brightness_step', 50))
        self.color_temperature_step =\
            int(self.config.get('color_temperature_step', 1000))
        self.verbose = True if self.config.get('verbose') == 'True' else False
        self.ip = self.config.get('ip')
        if not self.ip:
            self.ip = _discover_bridge()
        self.bridge = None
        self.all_lights = None

    @property
    def connected(self):
        return self.bridge is not None

    def _connect_to_bridge(self):
        try:
            self.bridge = Bridge(self.ip)
        except PhueRegistrationException:
            self.speak_dialog('connect.to.bridge')
            i = 0
            while i < 30:
                time.sleep(3)
                try:
                    self.bridge = Bridge(self.ip)
                except PhueRegistrationException:
                    continue
                else:
                    break
            if not self.connected:
                self.speak_dialog('failed.to.connect')
                return False
            else:
                self.speak_dialog('successfully.connected')
        self.all_lights = Group(self.bridge, 0)
        return True

    def initialize(self):
        self.load_data_files(dirname(__file__))

        turn_off_intent = IntentBuilder("TurnOffIntent"). \
            require("TurnOffKeyword").build()
        self.register_intent(turn_off_intent, self.handle_turn_off_intent)

        turn_on_intent = IntentBuilder("TurnOnIntent"). \
            require("TurnOnKeyword").build()
        self.register_intent(turn_on_intent,
                             self.handle_turn_on_intent)

        activate_scene_intent = IntentBuilder("ActivateScene"). \
            require("ActivateSceneKeyword").build()
        self.register_intent(activate_scene_intent,
                             self.handle_activate_scene_intent)

        decrease_brightness_intent = IntentBuilder("DecreaseBrightnessIntent"). \
            require("DecreaseBrightnessKeyword").build()
        self.register_intent(decrease_brightness_intent,
                             self.decrease_brightness_intent)

        increase_brightness_intent = IntentBuilder("IncreaseBrightnessIntent"). \
            require("IncreaseBrightnessKeyword").build()
        self.register_intent(increase_brightness_intent,
                             self.increase_brightness_intent)

        decrease_color_temperature_intent = IntentBuilder("DecreaseColorTemperatureIntent"). \
            require("DecreaseColorTemperatureKeyword").build()
        self.register_intent(decrease_color_temperature_intent,
                             self.decrease_color_temperature_intent)

        increase_color_temperature_intent = IntentBuilder("IncreaseColorTemperatureIntent"). \
            require("IncreaseColorTemperatureKeyword").build()
        self.register_intent(increase_color_temperature_intent,
                             self.increase_color_temperature_intent)

    def handle_turn_off_intent(self, message):
        if self.verbose:
            self.speak_dialog('turn.off')
        if self.connected or self._connect_to_bridge():
            self.all_lights.on = False

    def handle_turn_on_intent(self, message):
        if self.verbose:
            self.speak_dialog('turn.on')
        if self.connected or self._connect_to_bridge():
            self.all_lights.on = True

    def handle_activate_scene_intent(self, message):
        if self.connected or self._connect_to_bridge():
            keyword_len = len(message.metadata['ActivateSceneKeyword'])
            scene_name = message.metadata['utterance'][keyword_len:].strip()
            if scene_name == '':
                self.speak_dialog('no.scene.name')
            else:
                scene_id = self.bridge.get_scene_id_from_name(
                    scene_name, case_sensitive=False)
                if scene_id:
                    if self.verbose:
                        self.speak_dialog('activate.scene',
                                          {'scene': scene_name})
                    self.bridge.activate_scene(scene_id)
                else:
                    self.speak_dialog('scene.not.found',
                                      {'scene': scene_name})

    def decrease_brightness_intent(self, message):
        if self.connected or self._connect_to_bridge():
            if self.verbose:
                self.speak_dialog('decrease.brightness')
            brightness = self.all_lights.brightness - self.brightness_step
            self.all_lights.brightness = brightness if brightness > 0 else 0

    def increase_brightness_intent(self, message):
        if self.connected or self._connect_to_bridge():
            if self.verbose:
                self.speak_dialog('increase.brightness')
            brightness = self.all_lights.brightness + self.brightness_step
            self.all_lights.brightness = brightness if brightness < 255 else 254

    def decrease_color_temperature_intent(self, message):
        if self.connected or self._connect_to_bridge():
            if self.verbose:
                self.speak_dialog('decrease.color.temperature')
            color_temperature = self.all_lights.colortemp_k - self.color_temperature_step
            self.all_lights.colortemp_k = color_temperature if color_temperature > 2000 else 2000

    def increase_color_temperature_intent(self, message):
        if self.connected or self._connect_to_bridge():
            if self.verbose:
                self.speak_dialog('increase.color.temperature')
            color_temperature = self.all_lights.colortemp_k + self.color_temperature_step
            self.all_lights.colortemp_k = color_temperature if color_temperature < 6500 else 6500

    def stop(self):
        pass


def _discover_bridge():
    """
    Naive method to find a phillips hue bridge on
    the network.

    Returns
    -------
    str
        An IP address representing the bridge that was found
    """
    SSDP_ADDR = "239.255.255.250"
    SSDP_PORT = 1900
    SSDP_MX = 1
    SSDP_ST = "urn:schemas-upnp-org:device:Basic:1"

    ssdpRequest = "M-SEARCH * HTTP/1.1\r\n" + \
                  "HOST: %s:%d\r\n" % (SSDP_ADDR, SSDP_PORT) + \
                  "MAN: \"ssdp:discover\"\r\n" + \
                  "MX: %d\r\n" % (SSDP_MX,) + \
                  "ST: %s\r\n" % (SSDP_ST,) + "\r\n"

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.sendto(ssdpRequest, (SSDP_ADDR, SSDP_PORT))
    result = sock.recv(4096)
    lines = result.splitlines()
    location_index = None
    for i in range(len(lines)):
        if lines[i].startswith('hue-bridgeid'):
            location_index = i - 2
            break
    if not location_index:
        raise DeviceNotFoundException()

    return lines[location_index].split('/')[2]


def create_skill():
    return PhillipsHueSkill()
