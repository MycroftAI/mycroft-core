from os.path import dirname

from adapt.intent import IntentBuilder
from mycroft.skills.core import MycroftSkill
from mycroft.util.log import getLogger

import socket
from phue import Bridge
from phue import Group
from phue import PhueRegistrationException
import time

__author__ = 'ChristopherRogers1991'

LOGGER = getLogger(__name__)

class DeviceNotFoundException(Exception):
    pass

class PhillipsHueSkill(MycroftSkill):


    def __init__(self):
        super(PhillipsHueSkill, self).__init__(name="PhillipsHueSkill")
        self.ip = self.config.get('ip')
        if not self.ip:
           self.ip = _discover_bridge()
        self.bridge = None # Bridge(self.ip)
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

    def handle_turn_off_intent(self, message):
        if self.connected or self._connect_to_bridge():
            self.all_lights.on = False

    def handle_turn_on_intent(self, message):
        if self.connected or self._connect_to_bridge():
            self.all_lights.on = True

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
    lines = result.readline()
    location_index = None
    for i in range(lines):
        if lines[i].startswith('hue-bridgeid'):
            location_index = i - 2
            break
    if not location_index:
        raise DeviceNotFoundException()

    return lines[location_index].split('/')[2]


def create_skill():
    return PhillipsHueSkill()
