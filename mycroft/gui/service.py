import asyncio
import json
from collections import namedtuple
from threading import Lock

import tornado.web as web
from tornado import ioloop
from tornado.websocket import WebSocketHandler

from mycroft.configuration import Configuration
from mycroft.messagebus.client import MessageBusClient
from mycroft.messagebus.message import Message
from mycroft.util import create_daemon, start_message_bus_client
from mycroft.util.log import LOG

Namespace = namedtuple('Namespace', ['name', 'pages'])
write_lock = Lock()
namespace_lock = Lock()

RESERVED_KEYS = ['__from', '__idle']
gui_app_settings = {
    'debug': True
}


class GUIService:
    def __init__(self):
        self.global_config = Configuration.get()
        # Create Message Bus Client
        self.bus = MessageBusClient()

        self.gui_protocol = self.create_gui_socket()

        # This datastore holds the data associated with the GUI provider. Data
        # is stored in Namespaces, so you can have:
        # self.datastore["namespace"]["name"] = value
        # Typically the namespace is a meaningless identifier, but there is a
        # special "SYSTEM" namespace.
        self.datastore = {}

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

        # Listen for new GUI clients to announce themselves on the main bus
        self.active_namespaces = []
        self.bus.on("mycroft.gui.connected", self.on_gui_client_connected)

        # First send any data:
        self.bus.on("gui.value.set", self.on_gui_set_value)
        self.bus.on("gui.page.show", self.on_gui_show_page)
        self.bus.on("gui.page.delete", self.on_gui_delete_page)
        self.bus.on("gui.clear.namespace", self.on_gui_delete_namespace)
        self.bus.on("gui.event.send", self.on_gui_send_event)
        self.bus.on("gui.status.request", self.handle_gui_status_request)

    def create_gui_socket(self):
        import tornado.options
        LOG.info('Starting message bus for GUI...')
        # Disable all tornado logging so mycroft loglevel isn't overridden
        tornado.options.parse_command_line(['--logging=None'])
        config = self.global_config['gui_websocket']

        routes = [(config['route'], GUIWebsocketHandler)]
        application = web.Application(routes, debug=True)
        application.service = self
        application.listen(config['base_port'], config['host'])

        create_daemon(ioloop.IOLoop.instance().start)
        LOG.info('GUI Message bus started!')
        return application

    def run(self):
        """Start the GUI after it has been constructed."""
        # Allow exceptions to be raised to the GUI Service
        # if they may cause the Service to fail.
        start_message_bus_client("GUI_SERVICE", self.bus)

    def stop(self):
        """Perform any GUI shutdown processes."""
        pass

    ######################################################################
    # GUI client API
    @property
    def gui_connected(self):
        """Returns True if at least 1 gui is connected, else False"""
        return len(GUIWebsocketHandler.clients) > 0

    def handle_gui_status_request(self, message):
        """Reply to gui status request, allows querying if a gui is
        connected using the message bus"""
        self.bus.emit(message.reply("gui.status.request.response",
                                    {"connected": self.gui_connected}))

    def send(self, msg_dict):
        """ Send to all registered GUIs. """
        for connection in GUIWebsocketHandler.clients:
            try:
                connection.send(msg_dict)
            except Exception as e:
                LOG.exception(repr(e))

    def on_gui_send_event(self, message):
        """ Send an event to the GUIs. """
        try:
            data = {'type': 'mycroft.events.triggered',
                    'namespace': message.data.get('__from'),
                    'event_name': message.data.get('event_name'),
                    'params': message.data.get('params')}
            self.send(data)
        except Exception as e:
            LOG.error('Could not send event ({})'.format(repr(e)))

    def on_gui_set_value(self, message):
        data = message.data
        namespace = data.get("__from", "")

        # Pass these values on to the GUI renderers
        for key in data:
            if key not in RESERVED_KEYS:
                try:
                    self.set(namespace, key, data[key])
                except Exception as e:
                    LOG.exception(repr(e))

    def set(self, namespace, name, value):
        """ Perform the send of the values to the connected GUIs. """
        if namespace not in self.datastore:
            self.datastore[namespace] = {}
        if self.datastore[namespace].get(name) != value:
            self.datastore[namespace][name] = value

            # If the namespace is loaded send data to GUI
            if namespace in [l.name for l in self.loaded]:
                msg = {"type": "mycroft.session.set",
                       "namespace": namespace,
                       "data": {name: value}}
                self.send(msg)

    def on_gui_delete_page(self, message):
        """ Bus handler for removing pages. """
        page, namespace, _ = self._get_page_data(message)
        try:
            with namespace_lock:
                self.remove_pages(namespace, page)
        except Exception as e:
            LOG.exception(repr(e))

    def on_gui_delete_namespace(self, message):
        """ Bus handler for removing namespace. """
        try:
            namespace = message.data['__from']
            with namespace_lock:
                self.remove_namespace(namespace)
        except Exception as e:
            LOG.exception(repr(e))

    def on_gui_show_page(self, message):
        try:
            page, namespace, index = self._get_page_data(message)
            # Pass the request to the GUI(s) to pull up a page template
            with namespace_lock:
                self.show(namespace, page, index)
        except Exception as e:
            LOG.exception(repr(e))

    @staticmethod
    def _get_page_data(message):
        """ Extract page related data from a message.

        Args:
            message: messagebus message object
        Returns:
            tuple (page, namespace, index)
        Raises:
            ValueError if value is missing.
        """
        data = message.data
        # Note:  'page' can be either a string or a list of strings
        if 'page' not in data:
            raise ValueError("Page missing in data")
        if 'index' in data:
            index = data['index']
        else:
            index = 0
        page = data.get("page", "")
        namespace = data.get("__from", "")
        return page, namespace, index

    def __find_namespace(self, namespace):
        for i, skill in enumerate(self.loaded):
            if skill[0] == namespace:
                return i
        return None

    def __insert_pages(self, namespace, pages):
        """ Insert pages into the namespace

        Args:
            namespace (str): Namespace to add to
            pages (list):    Pages (str) to insert
        """
        LOG.debug("Inserting new pages")
        if not isinstance(pages, list):
            raise ValueError('Argument must be list of pages')

        self.send({"type": "mycroft.gui.list.insert",
                   "namespace": namespace,
                   "position": len(self.loaded[0].pages),
                   "data": [{"url": p} for p in pages]
                   })
        # Insert the pages into local reprensentation as well.
        updated = Namespace(self.loaded[0].name, self.loaded[0].pages + pages)
        self.loaded[0] = updated

    def __remove_page(self, namespace, pos):
        """ Delete page.

        Args:
            namespace (str): Namespace to remove from
            pos (int):      Page position to remove
        """
        LOG.debug("Deleting {} from {}".format(pos, namespace))
        self.send({"type": "mycroft.gui.list.remove",
                   "namespace": namespace,
                   "position": pos,
                   "items_number": 1
                   })
        # Remove the page from the local reprensentation as well.
        self.loaded[0].pages.pop(pos)
        # Add a check to return any display to idle from position 0
        if (pos == 0 and len(self.loaded[0].pages) == 0):
            self.bus.emit(Message("mycroft.device.show.idle"))

    def __insert_new_namespace(self, namespace, pages):
        """ Insert new namespace and pages.

        This first sends a message adding a new namespace at the
        highest priority (position 0 in the namespace stack)

        Args:
            namespace (str):  The skill namespace to create
            pages (str):      Pages to insert (name matches QML)
        """
        LOG.debug("Inserting new namespace")
        self.send({"type": "mycroft.session.list.insert",
                   "namespace": "mycroft.system.active_skills",
                   "position": 0,
                   "data": [{"skill_id": namespace}]
                   })

        # Load any already stored Data
        data = self.datastore.get(namespace, {})
        for key in dict(data):
            msg = {"type": "mycroft.session.set",
                   "namespace": namespace,
                   "data": {key: data[key]}}
            self.send(msg)

        LOG.debug("Inserting new page")
        self.send({"type": "mycroft.gui.list.insert",
                   "namespace": namespace,
                   "position": 0,
                   "data": [{"url": p} for p in pages]
                   })
        # Make sure the local copy is updated
        self.loaded.insert(0, Namespace(namespace, pages))

    def __move_namespace(self, from_pos, to_pos):
        """ Move an existing namespace to a new position in the stack.

        Args:
            from_pos (int): Position in the stack to move from
            to_pos (int): Position to move to
        """
        LOG.debug("Activating existing namespace")
        # Seems like the namespace is moved to the top automatically when
        # a page change is done. Deactivating this for now.
        if self.explicit_move:
            LOG.debug("move {} to {}".format(from_pos, to_pos))
            self.send({"type": "mycroft.session.list.move",
                       "namespace": "mycroft.system.active_skills",
                       "from": from_pos, "to": to_pos,
                       "items_number": 1})
        # Move the local representation of the skill from current
        # position to position 0.
        self.loaded.insert(to_pos, self.loaded.pop(from_pos))

    def __switch_page(self, namespace, pages):
        """ Switch page to an already loaded page.

        Args:
            pages (list): pages (str) to switch to
            namespace (str):  skill namespace
        """
        try:
            num = self.loaded[0].pages.index(pages[0])
        except Exception as e:
            LOG.exception(repr(e))
            num = 0

        LOG.debug('Switching to already loaded page at '
                  'index {} in namespace {}'.format(num, namespace))
        self.send({"type": "mycroft.events.triggered",
                   "namespace": namespace,
                   "event_name": "page_gained_focus",
                   "data": {"number": num}})

    def show(self, namespace, page, index):
        """ Show a page and load it as needed.

        Args:
            page (str or list): page(s) to show
            namespace (str):  skill namespace
            index (int): ??? TODO: Unused in code ???

        TODO: - Update sync to match.
              - Separate into multiple functions/methods
        """

        LOG.debug("GUIConnection activating: " + namespace)
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
            LOG.exception(repr(e))

    def remove_namespace(self, namespace):
        """ Remove namespace.

        Args:
            namespace (str): namespace to remove
        """
        index = self.__find_namespace(namespace)
        if index is None:
            return
        else:
            LOG.debug("Removing namespace {} at {}".format(namespace, index))
            self.send({"type": "mycroft.session.list.remove",
                       "namespace": "mycroft.system.active_skills",
                       "position": index,
                       "items_number": 1
                       })
            # Remove namespace from loaded namespaces
            self.loaded.pop(index)

    def remove_pages(self, namespace, pages):
        """ Remove the listed pages from the provided namespace.

        Args:
            namespace (str):    The namespace to modify
            pages (list):       List of page names (str) to delete
        """
        try:
            index = self.__find_namespace(namespace)
            if index is None:
                return
            else:
                # Remove any pages that doesn't exist in the namespace
                pages = [p for p in pages if p in self.loaded[index].pages]
                # Make sure to remove pages from the back
                indexes = [self.loaded[index].pages.index(p) for p in pages]
                indexes = sorted(indexes)
                indexes.reverse()
                for page_index in indexes:
                    self.__remove_page(namespace, page_index)
        except Exception as e:
            LOG.exception(repr(e))

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
        LOG.info('GUI HAS ANNOUNCED!')
        port = self.global_config["gui_websocket"]["base_port"]
        LOG.debug("on_gui_client_connected")
        gui_id = message.data.get("gui_id")

        LOG.debug("Heard announcement from gui_id: {}".format(gui_id))

        # Announce connection, the GUI should connect on it soon
        self.bus.emit(Message("mycroft.gui.port",
                              {"port": port,
                               "gui_id": gui_id}))


class GUIWebsocketHandler(WebSocketHandler):
    """The socket pipeline between the GUI and Mycroft."""
    clients = []

    def open(self):
        GUIWebsocketHandler.clients.append(self)
        LOG.info('New Connection opened!')
        self.synchronize()

    def on_close(self, *args):
        LOG.info('Closing {}'.format(id(self)))
        GUIWebsocketHandler.clients.remove(self)

    def synchronize(self):
        """ Upload namespaces, pages and data to the last connected. """
        namespace_pos = 0
        service = self.application.service

        for namespace, pages in service.loaded:
            LOG.info('Sync {}'.format(namespace))
            # Insert namespace
            self.send({"type": "mycroft.session.list.insert",
                       "namespace": "mycroft.system.active_skills",
                       "position": namespace_pos,
                       "data": [{"skill_id": namespace}]
                       })
            # Insert pages
            self.send({"type": "mycroft.gui.list.insert",
                       "namespace": namespace,
                       "position": 0,
                       "data": [{"url": p} for p in pages]
                       })
            # Insert data
            data = service.datastore.get(namespace, {})
            for key in data:
                self.send({"type": "mycroft.session.set",
                           "namespace": namespace,
                           "data": {key: data[key]}
                           })
            namespace_pos += 1

    def on_message(self, *args):
        if len(args) == 1:
            message = args[0]
        else:
            message = args[1]
        LOG.info("Received: {}".format(message))
        msg = json.loads(message)
        if (msg.get('type') == "mycroft.events.triggered" and
                (msg.get('event_name') == 'page_gained_focus' or
                 msg.get('event_name') == 'system.gui.user.interaction')):
            # System event, a page was changed
            msg_type = 'gui.page_interaction'
            msg_data = {'namespace': msg['namespace'],
                        'page_number': msg['parameters'].get('number'),
                        'skill_id': msg['parameters'].get('skillId')}
        elif msg.get('type') == "mycroft.events.triggered":
            # A normal event was triggered
            msg_type = '{}.{}'.format(msg['namespace'], msg['event_name'])
            msg_data = msg['parameters']

        elif msg.get('type') == 'mycroft.session.set':
            # A value was changed send it back to the skill
            msg_type = '{}.{}'.format(msg['namespace'], 'set')
            msg_data = msg['data']

        message = Message(msg_type, msg_data)
        LOG.info('Forwarding to bus...')
        self.application.service.bus.emit(message)
        LOG.info('Done!')

    def write_message(self, *arg, **kwarg):
        """Wraps WebSocketHandler.write_message() with a lock. """
        try:
            asyncio.get_event_loop()
        except RuntimeError:
            asyncio.set_event_loop(asyncio.new_event_loop())

        with write_lock:
            super().write_message(*arg, **kwarg)

    def send(self, data):
        """Send the given data across the socket as JSON

        Args:
            data (dict): Data to transmit
        """
        s = json.dumps(data)
        LOG.info('Sending {}'.format(s))
        self.write_message(s)

    def check_origin(self, origin):
        """Disable origin check to make js connections work."""
        return True
