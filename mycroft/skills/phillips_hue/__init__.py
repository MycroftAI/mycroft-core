from adapt.intent import IntentBuilder
from mycroft.skills.core import MycroftSkill
from mycroft.util.log import getLogger
from os.path import dirname
from phue import Bridge
from phue import Group
from phue import PhueRegistrationException
from phue import PhueRequestTimeout
from time import sleep
import socket

__author__ = 'ChristopherRogers1991'

LOGGER = getLogger(__name__)


class DeviceNotFoundException(Exception):
    pass


class PhillipsHueSkill(MycroftSkill):

    def __init__(self):
        super(PhillipsHueSkill, self).__init__(name="PhillipsHueSkill")
        self.brightness_step = int(self.config.get('brightness_step'))
        self.color_temperature_step =\
            int(self.config.get('color_temperature_step'))
        self.verbose = True if self.config.get('verbose') == 'True' else False
        self.username = self.config.get('username', '')
        if self.username == '':
            self.username = None
        self.ip = None  # set in _connect_to_bridge
        self.user_supplied_ip = True
        self.bridge = None
        self.all_lights = None

    @property
    def connected(self):
        return self.bridge is not None

    def _register_with_bridge(self):
        self.speak_dialog('connect.to.bridge')
        i = 0
        while i < 30:
            sleep(1)
            try:
                self.bridge = Bridge(self.ip)
            except PhueRegistrationException:
                continue
            else:
                break
        if not self.connected:
            self.speak_dialog('failed.to.register')
            return False
        else:
            self.speak_dialog('successfully.registered')

    def _connect_to_bridge(self, acknowledge_successful_connection=False):
        try:
            self.ip = self.config.get('ip')
            if self.ip == '':
                self.user_supplied_ip = False
                self.ip = _discover_bridge()
            self.bridge = Bridge(self.ip, self.username)
        except DeviceNotFoundException:
            self.speak_dialog('bridge.not.found')
            return False
        except PhueRegistrationException:
            self._register_with_bridge()
        try:
            self.all_lights = Group(self.bridge, 0)
            self.username = self.bridge.username
        except Exception as e:
            if 'No route to host' in e.args:
                self.speak_dialog('no.route')
            else:
                self.speak_dialog('failed.to.connect')
            return False
        if acknowledge_successful_connection:
            self.speak_dialog('successfully.connected')
        return True

    def initialize(self):
        self.load_data_files(dirname(__file__))

        turn_off_intent = IntentBuilder("TurnOffIntent")\
            .require("TurnOffKeyword").build()
        self.register_intent(turn_off_intent, self.handle_intent)

        turn_on_intent = IntentBuilder("TurnOnIntent")\
            .require("TurnOnKeyword").build()
        self.register_intent(turn_on_intent, self.handle_intent)

        activate_scene_intent = IntentBuilder("ActivateSceneIntent")\
            .require("ActivateSceneKeyword").build()
        self.register_intent(activate_scene_intent,
                             self.handle_intent)

        decrease_brightness_intent = IntentBuilder("DecreaseBrightnessIntent")\
            .require("DecreaseBrightnessKeyword").build()
        self.register_intent(decrease_brightness_intent,
                             self.handle_intent)

        increase_brightness_intent = IntentBuilder("IncreaseBrightnessIntent")\
            .require("IncreaseBrightnessKeyword").build()
        self.register_intent(increase_brightness_intent,
                             self.handle_intent)

        decrease_color_temperature_intent =\
            IntentBuilder("DecreaseColorTemperatureIntent")\
            .require("DecreaseColorTemperatureKeyword").build()
        self.register_intent(decrease_color_temperature_intent,
                             self.handle_intent)

        increase_color_temperature_intent =\
            IntentBuilder("IncreaseColorTemperatureIntent")\
            .require("IncreaseColorTemperatureKeyword").build()
        self.register_intent(increase_color_temperature_intent,
                             self.handle_intent)

        connect_lights_intent = \
            IntentBuilder("ConnectLightsIntent") \
            .require("ConnectLightsKeyword").build()
        self.register_intent(connect_lights_intent,
                             self.handle_intent)

    def handle_intent(self, message):
        if message.message_type == 'ConnectLightsIntent'\
                or self.connected or self._connect_to_bridge():
            try:
                if message.message_type == "TurnOffIntent":
                    self.handle_turn_off_intent(message)
                elif message.message_type == "TurnOnIntent":
                    self.handle_turn_on_intent(message)
                elif message.message_type == "ActivateSceneIntent":
                    self.handle_activate_scene_intent(message)
                elif message.message_type == "DecreaseBrightnessIntent":
                    self.handle_decrease_brightness_intent(message)
                elif message.message_type == "IncreaseBrightnessIntent":
                    self.handle_increase_brightness_intent(message)
                elif message.message_type == "DecreaseColorTemperatureIntent":
                    self.handle_decrease_color_temperature_intent(message)
                elif message.message_type == "IncreaseColorTemperatureIntent":
                    self.handle_increase_color_temperature_intent(message)
                elif message.message_type == "ConnectLightsIntent":
                    self.handle_connect_lights_intent(message)
                else:
                    raise Exception('No matching intent handler')
            except Exception as e:
                if isinstance(e, PhueRequestTimeout):
                    self.speak_dialog('unable.to.perform.action')
                elif 'No route to host' in e.args:
                    if self.user_supplied_ip:
                        self.speak_dialog('no.route')
                        return
                    else:
                        self.speak_dialog('could.not.communicate')
                        if self._connect_to_bridge(True):
                            self.handle_intent(message)
                else:
                    raise

    def handle_turn_off_intent(self, message):
        if self.verbose:
            self.speak_dialog('turn.off')
        self.all_lights.on = False

    def handle_turn_on_intent(self, message):
        if self.verbose:
            self.speak_dialog('turn.on')
        self.all_lights.on = True

    def handle_activate_scene_intent(self, message):
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

    def handle_decrease_brightness_intent(self, message):
        if self.verbose:
            self.speak_dialog('decrease.brightness')
        brightness = self.all_lights.brightness - self.brightness_step
        self.all_lights.brightness = brightness if brightness > 0 else 0

    def handle_increase_brightness_intent(self, message):
        if self.verbose:
            self.speak_dialog('increase.brightness')
        brightness = self.all_lights.brightness + self.brightness_step
        self.all_lights.brightness =\
            brightness if brightness < 255 else 254

    def handle_decrease_color_temperature_intent(self, message):
        if self.verbose:
            self.speak_dialog('decrease.color.temperature')
        color_temperature =\
            self.all_lights.colortemp_k - self.color_temperature_step
        self.all_lights.colortemp_k =\
            color_temperature if color_temperature > 2000 else 2000

    def handle_increase_color_temperature_intent(self, message):
        if self.verbose:
            self.speak_dialog('increase.color.temperature')
        color_temperature =\
            self.all_lights.colortemp_k + self.color_temperature_step
        self.all_lights.colortemp_k =\
            color_temperature if color_temperature < 6500 else 6500

    def handle_connect_lights_intent(self, message):
        if self.user_supplied_ip:
            self.speak_dialog('ip.in.config')
            return
        if self.verbose:
            self.speak_dialog('connecting')
        self._connect_to_bridge(acknowledge_successful_connection=True)

    def stop(self):
        pass


def _discover_bridge():
    """
    Naive method to find a phillips hue bridge on
    the network, via UPNP.

    Raises
    ------
    DeviceNotFoundException
        If the bridge is not found.

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
    sock.settimeout(5.0)
    sock.sendto(ssdpRequest, (SSDP_ADDR, SSDP_PORT))
    try:
        result = sock.recv(4096)
        lines = result.splitlines()
        for i in range(len(lines)):
            if lines[i].startswith('hue-bridgeid'):
                location_index = i - 2
                sock.close()
                return lines[location_index].split('/')[2]
    except:
        pass
    raise DeviceNotFoundException()


def create_skill():
    return PhillipsHueSkill()
