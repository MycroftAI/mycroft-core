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
from collections import namedtuple

from mycroft.configuration import Configuration
from mycroft.messagebus.client.ws import WebsocketClient
from mycroft.util import create_daemon
from mycroft.util.log import LOG

import tornado.web
import json
from tornado import autoreload, ioloop
from tornado.websocket import WebSocketHandler
from mycroft.messagebus.message import Message


Namespace = namedtuple('Namespace', ['name', 'pages'])


def DEBUG(str):
    print(str)
    # pass  # disable by default


class Enclosure:

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
        self.active_namespaces = []
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
    # GUI client API

    def _gui_activate(self, namespace, move_to_top=False):
        if not namespace:
            return

        if namespace not in self.active_namespaces:
            if move_to_top:
                self.active_namespaces.insert(0, namespace)
            else:
                self.active_namespaces.append(namespace)
        elif move_to_top:
            self.active_namespaces.remove(namespace)
            self.active_namespaces.insert(0, namespace)
        # TODO: Keep a timestamp and auto-cull?

    def on_gui_set_value(self, message):
        data = message.data
        namespace = data.get("__from", "")

        self._gui_activate(namespace)

        # Pass these values on to the GUI renderers
        for id in self.GUIs:
            for key in data:
                if key != "__from":
                    self.GUIs[id].set(namespace, key, data[key])

    def on_gui_show_page(self, message):
        data = message.data

        # Note:  'page' can be either a string or a list of strings
        if 'page' not in data:
            return
        if 'index' in data:
            index = data['index']
        else:
            index = 0
        namespace = data.get("__from", "")
        self._gui_activate(namespace, move_to_top=True)

        # Pass the request to the GUI(s) to pull up a page template
        for id in self.GUIs:
            self.GUIs[id].show(namespace, data['page'], index)

    ######################################################################
    # GUI client socket
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
        DEBUG("on_gui_client_connected")
        gui_id = message.data.get("gui_id")

        # Spin up a new communication socket for this GUI
        if gui_id in self.GUIs:
            # TODO: Close it?
            pass
        self.GUIs[gui_id] = GUIConnection(gui_id, self.global_config,
                                          self.callback_disconnect, self)
        DEBUG("Heard announcement from gui_id: {}".format(gui_id))

        # Announce connection, the GUI should connect on it soon
        self.bus.emit(Message("mycroft.gui.port",
                              {"port": self.GUIs[gui_id].port,
                               "gui_id": gui_id}))

    def callback_disconnect(self, gui_id):
        DEBUG("Disconnecting!")
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


class GUIConnection:
    """ A single GUIConnection exists per graphic interface.  This object
    maintains the socket used for communication and keeps the state of the
    Mycroft data in sync with the GUIs data.

    Serves as a communication interface between Qt/QML frontend and Mycroft
    Core.  This is bidirectional, e.g. "show me this visual" to the frontend as
    well as "the user just tapped this button" from the frontend.

    For the rough protocol, see:
    https://cgit.kde.org/scratch/mart/mycroft-gui.git/tree/transportProtocol.txt?h=newapi  # nopep8

    TODO: Implement variable deletion
    TODO: Implement 'models' support
    TODO: Implement events
    TODO: Implement data coming back from Qt to Mycroft
    """

    _last_idx = 0  # this is incremented by 1 for each open GUIConnection
    server_thread = None

    def __init__(self, id, config, callback_disconnect, enclosure):
        DEBUG("Creating GUIConnection")
        self.id = id
        self.socket = None
        self.callback_disconnect = callback_disconnect
        self.enclosure = enclosure
        self._active_namespaces = None

        # This datastore holds the data associated with the GUI provider.  Data
        # is stored in Namespaces, so you can have:
        #   self.datastore["namespace"]["name"] = value
        # Typically the namespace is a meaningless identifier, but there is a
        # special "SYSTEM" namespace.
        self.datastore = {}

        self.current_namespace = None
        self.current_pages = []
        self.current_index = None

        # self.loaded is a list, each element consists of a namespace named
        # tuple.
        # The namespace namedtuple has the properties "name" and "pages"
        # The name contains the namespace name as a string and pages is a
        # mutable list of loaded pages.
        #
        # [Namespace name, [List of loaded qml pages]]
        # [
        # ["SKILL_NAME", ["page1.qml, "page2.qml", ... , "pageN.qml"]
        # [...]
        # ]
        self.loaded = []  # list of lists in order.
        self.explicit_move = True  # Set to true to send reorder commands

        # Each connection will run its own Tornado server.  If the
        # connection drops, the server is killed.
        websocket_config = config.get("gui_websocket")
        host = websocket_config.get("host")
        route = websocket_config.get("route")
        self.port = websocket_config.get("base_port") + GUIConnection._last_idx
        GUIConnection._last_idx += 1

        try:
            self.webapp = tornado.web.Application([
                                                   (route, GUIWebsocketHandler)
                                                  ], **gui_app_settings)
            self.webapp.gui = self  # Hacky way to associate socket with this
            self.webapp.listen(self.port, host)
        except Exception as e:
            DEBUG('Error: {}'.format(repr(e)))
        # Can't run two IOLoop's in the same process
        if not GUIConnection.server_thread:
            GUIConnection.server_thread = create_daemon(
                ioloop.IOLoop.instance().start)
        DEBUG("IOLoop started @ ws://{}:{}{}".format(host, self.port, route))

    def on_connection_opened(self, socket_handler):
        DEBUG("on_connection_opened")
        self.socket = socket_handler

        # Synchronize existing datastore
        for namespace in self.datastore:
            msg = {"type": "mycroft.session.set",
                   "namespace": namespace,
                   "data": self.datastore[namespace]}
            self.socket.send_message(msg)
        # TODO REPLACE WITH CODE USING self.loaded
        # if self.current_pages:
        #    self.show(self.current_namespace, self.current_pages,
        #              self.current_index)

    def on_connection_closed(self, socket):
        # Self-destruct (can't reconnect on the same port)
        DEBUG("on_connection_closed")
        if self.socket:
            DEBUG("Server stopped: {}".format(self.socket))
            # TODO: How to stop the webapp for this socket?
            # self.socket.stop()
            self.socket = None
        self.callback_disconnect(self.id)

    def set(self, namespace, name, value):
        if namespace not in self.datastore:
            self.datastore[namespace] = {}
        if self.datastore[namespace].get(name) != value:
            self.datastore[namespace][name] = value

            # If the namespace is loaded send data to gui
            if namespace in [l.name for l in self.loaded]:
                msg = {"type": "mycroft.session.set",
                       "namespace": namespace,
                       "data": {name: value}}
                self.socket.send(msg)

    def __find_namespace(self, namespace):
        for i, skill in enumerate(self.loaded):
            if skill[0] == namespace:
                return i
        return None

    def __insert_pages(self, namespace, pages):
        """ Insert pages into the """
        DEBUG("Inserting new pages")
        if not isinstance(pages, list):
            raise ValueError('Argument must be list of pages')

        self.socket.send({"type": "mycroft.gui.list.insert",
                          "namespace": namespace,
                          "position": len(self.loaded[0].pages),
                          "data": [{"url": p} for p in pages]
                          })

        # append pages to local representation
        for p in pages:
            self.loaded[0].pages.append(p)

    def __insert_new_namespace(self, namespace, pages):
        """ Insert new namespace and pages.

            This first sends a message adding a new namespace at the
            highest priority (position 0 in the namespace stack)

            Arguments:
                namespace:  The skill namespace to create
                pages:      Pages to insert
        """
        DEBUG("Inserting new namespace")
        self.socket.send({"type": "mycroft.session.list.insert",
                          "namespace": "mycroft.system.active_skills",
                          "position": 0,
                          "data": [{"skill_id": namespace}]
                          })

        # Load any already stored Data
        data = self.datastore.get(namespace, {})
        for key in data:
            msg = {"type": "mycroft.session.set",
                   "namespace": namespace,
                   "data": {key: data[key]}}
            self.socket.send(msg)

        DEBUG("Inserting new page")
        self.socket.send({"type": "mycroft.gui.list.insert",
                          "namespace": namespace,
                          "position": 0,
                          "data": [{"url": p} for p in pages]
                          })
        # Make sure the local copy is updated
        self.loaded.insert(0, Namespace(namespace, pages))

    def __move_namespace(self, from_pos, to_pos):
        """ Move an existing namespace to a new position in the stack.

            Arguments:
                from_pos: Position in the stack to move from
                to_pos: Position to move to
        """
        DEBUG("Activating existing namespace")
        # Seems like the namespace is moved to the top automatically when
        # a page change is done. Deactivating this for now.
        if self.explicit_move:
            DEBUG("move {} to {}".format(from_pos, to_pos))
            self.socket.send({"type": "mycroft.session.list.move",
                              "namespace": "mycroft.system.active_skills",
                              "from": from_pos, "to": to_pos,
                              "items_number": 1})
        # Move the local representation of the skill from current
        # position to position 0.
        self.loaded.insert(to_pos, self.loaded.pop(from_pos))

    def __switch_page(self, namespace, pages):
        """ Switch page to an already loaded page.

            Arguments:
                pages:      pages to switch to
                namespace:  skill namespace
        """
        try:
            num = self.loaded[0].pages.index(pages[0])
        except Exception as e:
            DEBUG(e)
            num = 0

        DEBUG("Switching to already loaded page at "
              "index {} in namespace {}".format(num, namespace))
        self.socket.send({"type": "mycroft.events.triggered",
                          "namespace": namespace,
                          "event_name": "page_gained_focus",
                          "data": {"number": num}})

    def show(self, namespace, page, index):
        """ Show a page and load it as needed.

            TODO: - Update sync to match.
                  - Separate into multiple functions/methods
        """

        DEBUG("GUIConnection activating: " + namespace)
        pages = page if isinstance(page, list) else [page]

        # find namespace among loaded namespaces
        try:
            index = self.__find_namespace(namespace)
            if index is None:
                # This namespace doesn't exist, insert them first so they're
                # shown.
                self.__insert_new_namespace(namespace, pages)
                return
            else:  # Namespace exists
                if index > 0:
                    # Namespace is inactive, activate it by moving it to
                    # position 0
                    self.__move_namespace(index, 0)

                # Find if any new pages needs to be inserted
                new_pages = [p for p in pages if p not in self.loaded[0].pages]
                if new_pages:
                    self.__insert_pages(namespace, new_pages)
                else:
                    # No new pages, just switch
                    self.__switch_page(namespace, pages)
        except Exception as e:
            DEBUG(repr(e))

        # TODO: Not quite sure this is needed or if self.loaded can be used
        self.current_namespace = namespace
        self.current_pages = pages
        self.current_index = index


class GUIWebsocketHandler(WebSocketHandler):
    """
    The socket pipeline between Qt and Mycroft
    """

    def open(self):
        self.application.gui.on_connection_opened(self)

    def on_message(self, message):
        DEBUG("Received: {}".format(message))

    def send_message(self, message):
        self.write_message(message.serialize())

    def send(self, data):
        """Send the given data across the socket as JSON

        Args:
            data (dict): Data to transmit
        """
        s = json.dumps(data)
        self.write_message(s)

    def on_close(self):
        self.application.gui.on_connection_closed(self)
