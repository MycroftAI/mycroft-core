# Copyright 2017 Mycroft AI Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
import sys

from mycroft.configuration import Configuration
from mycroft.messagebus.client.ws import WebsocketClient
from mycroft.util import create_daemon
from mycroft.util.log import LOG

import tornado.web
import json
from tornado import autoreload, ioloop
from tornado.websocket import WebSocketHandler
from mycroft.messagebus.message import Message

class Enclosure(object):

    def __init__(self):
        # Establish Enclosure's websocket connection to the messagebus
        self.bus = WebsocketClient()

        # Load full config
        Configuration.init(self.bus)
        config = Configuration.get()

        self.lang = config['lang']
        self.config = config.get("enclosure")
        self.global_config = config

        # Listen for new GUI clients to announce themselves on the main bus
        self.GUIs = {}      # GUIs, either local or remote
        self.bus.on("mycroft.gui.connected", self.on_gui_client_connected)
        self.register_gui_handlers()

        # First send any data:
        self.bus.on("gui.value.set", self.on_gui_set_value)
        self.bus.on("gui.page.show", self.on_gui_show_page)


    def run(self):
        try:
            self.bus.run_forever()
        except Exception as e:
            LOG.error("Error: {0}".format(e))
            self.stop()

    ######################################################################
    # GUI client support
    #
    # The basic mechanism is:
    # 1) GUI client announces itself on the main messagebus
    # 2) Mycroft prepares a port for a socket connection to this GUI
    # 3) The port is announced over the messagebus
    # 4) The GUI connects on the socket
    # 5) Connection persists for graphical interaction indefinitely
    #
    # If the connection is lost, it must be renegotiated and restarted.

    def on_gui_client_connected(self, message):
        # GUI has announced presence
        print("on_gui_client_connected")
        gui_id = message.data.get("gui_id")

        # Spin up a new communication socket for this GUI
        if gui_id in self.GUIs:
            # TODO: Close it?
            pass
        self.GUIs[gui_id] = GUIConnection(gui_id, self.global_config,
                                          self.callback_disconnect)
        print("Heard announcement from gui_id: "+str(gui_id))

        # Announce connection, the GUI should connect on it soon
        self.bus.emit(Message("mycroft.gui.port",
                              {"port": self.GUIs[gui_id].port,
                               "gui_id": gui_id}))

    def on_gui_set_value(self, message):
        data = message.data

        # Pass these values on to the GUI renderers
        for id in self.GUIs:
            for d in data:
                self.GUIs[id].send('set '+d+' to '+data[d])    # TODO: Actually use the protocol

    def on_gui_show_page(self, message):
        data = message.data
        if not 'page' in data:
            return

        # Pass the display request to the GUI to pull up
        for id in self.GUIs:
            self.GUIs[id].send('show ' + data['page'])         # TODO: Actually use the protocol

    def callback_disconnect(self, gui_id):
        print("Disconnecting!")
        # TODO: Whatever is needed to kill the websocket instance
        del self.GUIs[gui_id]

    def register_gui_handlers(self):
        # TODO: Register handlers for standard (Mark 1) events
        # self.bus.on('enclosure.eyes.on', self.on)
        # self.bus.on('enclosure.eyes.off', self.off)
        # self.bus.on('enclosure.eyes.blink', self.blink)
        # self.bus.on('enclosure.eyes.narrow', self.narrow)
        # self.bus.on('enclosure.eyes.look', self.look)
        # self.bus.on('enclosure.eyes.color', self.color)
        # self.bus.on('enclosure.eyes.level', self.brightness)
        # self.bus.on('enclosure.eyes.volume', self.volume)
        # self.bus.on('enclosure.eyes.spin', self.spin)
        # self.bus.on('enclosure.eyes.timedspin', self.timed_spin)
        # self.bus.on('enclosure.eyes.reset', self.reset)
        # self.bus.on('enclosure.eyes.setpixel', self.set_pixel)
        # self.bus.on('enclosure.eyes.fill', self.fill)

        # self.bus.on('enclosure.mouth.reset', self.reset)
        # self.bus.on('enclosure.mouth.talk', self.talk)
        # self.bus.on('enclosure.mouth.think', self.think)
        # self.bus.on('enclosure.mouth.listen', self.listen)
        # self.bus.on('enclosure.mouth.smile', self.smile)
        # self.bus.on('enclosure.mouth.viseme', self.viseme)
        # self.bus.on('enclosure.mouth.text', self.text)
        # self.bus.on('enclosure.mouth.display', self.display)
        # self.bus.on('enclosure.mouth.display_image', self.display_image)
        # self.bus.on('enclosure.weather.display', self.display_weather)

        # self.bus.on('recognizer_loop:record_begin', self.mouth.listen)
        # self.bus.on('recognizer_loop:record_end', self.mouth.reset)
        # self.bus.on('recognizer_loop:audio_output_start', self.mouth.talk)
        # self.bus.on('recognizer_loop:audio_output_end', self.mouth.reset)
        pass


##########################################################################
# GUIConnection
##########################################################################

gui_app_settings = {
    'debug': True
}

class GUIConnection(object):

    last_used_port = 0
    server_thread = None

    def __init__(self, id, config, callback_disconnect):
        print("Creating GUIConnection")
        self.id = id
        self.server = None
        self.socket = None
        self.callback_disconnect = callback_disconnect

        # Each connection will run its own Tornado server.  If the
        # connection drops, the server is killed.
        websocket_config = config.get("gui_websocket")
        host = websocket_config.get("host")
        route = websocket_config.get("route")
        self.port = websocket_config.get("base_port") + GUIConnection.last_used_port
        GUIConnection.last_used_port += 1

        routes = [
            (route, MycroftGUIWebsocket)
        ]
        self.application = tornado.web.Application(routes, **gui_app_settings)
        self.application.gui = self
        self.server = self.application.listen(self.port, host)

        # TODO: This might need to move up a level
        # Can't run two IOLoop's in the same process
        if not GUIConnection.server_thread:
            GUIConnection.server_thread = create_daemon(ioloop.IOLoop.
                                                        instance().start)
        print("IOLoop started on ws://"+str(host)+":"+str(self.port)+str(route))

    def on_connection_opened(self, socket):
        print("on_connection_opened")
        self.socket = socket

    def on_connection_closed(self, socket):
        # Self-destruct (can't reconnect on the same port)
        print("on_connection_closed")
        if self.server:
            self.server.stop()
            self.server = None
        self.callback_disconnect(self.id)

class MycroftGUIWebsocket(WebSocketHandler):
    """
    Serves as a communication interface between Qt/QML frontend and Mycroft
    Core.  This is bidirectional, e.g. "show me this visual" to the frontend as
    well as "the user just tapped this button" from the frontend.

    For the rough protocol, see:
    https://cgit.kde.org/scratch/mart/mycroft-gui.git/tree/transportProtocol.txt?h=newapi  # nopep8
    """

    def open(self):
        print("WebSocket opened")
        self.application.gui.on_connection_opened(self)

        self.send(
            {
                "type": "mycroft.session.set",
                "namespace": "weather.mycroft",
                "data": {
                    "temperature": "28",
                    "icon": "cloudy"
                }
            }
        )

        self.send(
            {
                "type": "mycroft.gui.show",
                "namespace": "weather.mycroft",
                "gui_url": "file:///opt/mycroft/skills/mycroft-weather.mycroftai/ui/currentweather.qml"
            }
        )
        # self.send(Message("mycroft.gui.show", data={"namespace": "weather.mycroft", "gui_url": "file:///opt/mycroft/weather.mycroft/ui/currentweather.qml"}))

    def on_message(self, message):
        print("Received: "+str(message))
        # self.write_message(u"You said: " + message)
        # self.write_message(u"Then You said: " + message)

    def send_message(self, message):
        self.write_message(message.serialize())

    def send(self, data):
        s = json.dumps(data)
        self.write_message(s)
        print("Sent: "+s)

    def on_close(self):
        print("WebSocket closed")
        self.application.gui.on_connection_closed(self)
