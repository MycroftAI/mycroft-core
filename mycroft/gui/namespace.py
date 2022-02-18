# Copyright 2022 Mycroft AI Inc.
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
"""Defines the API for the QT GUI.

Manages what is displayed on a device with a touch screen using a LIFO stack
of "active" namespaces (e.g. skills).  At the bottom of the stack is the
namespace for the idle screen skill (if one is specified in the device
configuration).  The namespace for the idle screen skill should never be
removed from the stack.

When a skill with a GUI is triggered by the user, the namespace for that skill
is placed at the top of the stack.  The namespace at the top of the stack
represents the namespace that is visible on the device.  When the skill is
finished displaying information on the screen, it is removed from the top of
the stack.  This will result in the previously active namespace being
displayed.

The persistence of a namespace indicates how long that namespace stays in the
active stack.  A persistence expressed using a number represents how many
seconds the namespace will be active.  A persistence expressed with a True
value will be active until the skill issues a command to remove the namespace.
If a skill with a numeric persistence replaces a namespace at the top of the
stack that also has a numeric persistence, the namespace being replaced will
be removed from the active namespace stack.

The state of the active namespace stack is maintained locally and in the GUI
code.  Changes to namespaces, and their contents, are communicated to the GUI
over the GUI message bus.
"""
from threading import Lock, Timer
from typing import List, Union

from mycroft.configuration import Configuration
from mycroft.messagebus import Message, MessageBusClient
from mycroft.util.log import LOG
from .bus import (
    create_gui_service,
    determine_if_gui_connected,
    get_gui_websocket_config,
    send_message_to_gui
)

namespace_lock = Lock()

RESERVED_KEYS = ['__from', '__idle']


class Namespace:
    """A grouping mechanism for related GUI pages and data.

    In the majority of cases, a namespace represents a skill.  There is a
    SYSTEM namespace for GUI screens that exist outside of skills.  This class
    defines an API to manage a namespace, its pages and its data.  Actions
    are communicated to the GUI message bus.

    Attributes:
        name: the name of the Namespace, generally the skill ID
        persistent: indicates whether or not the namespace persists for a
            period of time or until the namespace is removed.
        duration: if the namespace persists for a period of time, this is the
            number of seconds of persistence
        pages: when the namespace is active, contains all the pages that are
            displayed at the same time
        data: a key/value pair representing the data used to populate the GUI
    """
    def __init__(self, name: str):
        self.name = name
        self.persistent = False
        self.duration = 30
        self.pages = list()
        self.data = dict()
        
    def add(self):
        """Adds a namespace to the list of active namespaces."""
        LOG.info(f"Adding \"{self.name}\" to active GUI namespaces")
        message = dict(
            type="mycroft.session.list.insert",
            namespace="mycroft.system.active_skills",
            position=0,
            data=[dict(skill_id=self.name)]
        )
        send_message_to_gui(message)

    def activate(self, position: int):
        """Activates an namespace already in the list of active namespaces."""
        LOG.info(f"Activating GUI namespace \"{self.name}\"")
        message = {
            "type": "mycroft.session.list.move",
            "namespace": "mycroft.system.active_skills",
            "from": position,
            "to": 0,
            "items_number": 1
        }
        send_message_to_gui(message)

    def remove(self, position: int):
        """Removes a namespace from the list of active namespaces."""
        LOG.info(f"Removing {self.name} from active GUI namespaces")
        message = dict(
            type="mycroft.session.list.remove",
            namespace="mycroft.system.active_skills",
            position=position,
            items_number=1
        )
        send_message_to_gui(message)
        self.pages = list()
        self.data = dict()

    def load_data(self, name: str, value: str):
        """Adds or changes the value of a namespace data attribute.

        Args:
            name: The name of the attribute
            value: The attribute's value
        """
        message = dict(
            type="mycroft.session.set",
            namespace=self.name,
            data={name: value}
        )
        send_message_to_gui(message)

    def set_persistence(self, persistence: Union[bool, int]):
        """Sets the duration of the namespace's time in the active list.

        Args:
            persistence: either the number of seconds before the namespace
                is removed or an indicator that the namespace should be
                active until it is explicitly removed.
        """
        if type(persistence) == int:
            self.duration = persistence
        elif type(persistence) == bool:
            self.persistent = True
        else:
            self.persistent = False
            self.duration = 30

        if self.persistent:
            LOG.info(f"GUI namespace {self.name} will persist until removed.")
        else:
            LOG.info(
                f"GUI namespace {self.name} will persist for "
                f"{self.duration} seconds."
            )

    def load_pages(self, pages: List[str]):
        """Maintains a list of active pages within the active namespace.

        Skills with multiple pages of data can either show all the screens
        at once, allowing the user to swipe back and forth among them, or
        the pages can be loaded one at a time.  The latter is represented by
        a single list item, the former by multiple list items

        Args:
            pages: one or more pages to be displayed
        """
        new_pages = [page for page in pages if page not in self.pages]
        self.pages.extend(new_pages)
        if new_pages:
            self._add_pages(new_pages)
        else:
            page = pages[0]

        self._activate_page(pages[0])

    def _add_pages(self, new_pages: List[str]):
        """Adds once or more pages to the active page list.

        Args:
            new_pages: pages to add to the active page list
        """
        LOG.info(f"Adding pages to GUI namespace {self.name}: {new_pages}")

        # Find position of new page in self.pages
        position = self.pages.index(new_pages[0])

        message = dict(
            type="mycroft.gui.list.insert",
            namespace=self.name,
            position=position,
            data=[dict(url=page) for page in new_pages]
        )
        send_message_to_gui(message)

    def _activate_page(self, page: str):
        """Returns focus to a page already in the active page list.

        Args:
            page: the page that will gain focus
        """
        LOG.info(f"Activating page {page} in GUI namespace {self.name}")
        page_index = self.pages.index(page)
        message = dict(
            type="mycroft.events.triggered",
            namespace=self.name,
            event_name="page_gained_focus",
            data=dict(number=page_index)
        )
        send_message_to_gui(message)

    def remove_pages(self, positions: List[int]):
        """Deletes one or more pages from the active page list.

        Args:
            positions: page position to remove
        """
        for position in positions:
            page = self.pages.pop(position)
            LOG.info(f"Deleting {page} from GUI namespace {self.name}")
            message = dict(
                type="mycroft.gui.list.remove",
                namespace=self.name,
                position=position,
                items_number=1
            )
            send_message_to_gui(message)


def _validate_page_message(message: Message):
    """Validates the contents of the message data for page add/remove messages.

    Args:
        message: A core message bus message to add/remove one or more pages
            from a namespace.
    """
    valid = (
        "page" in message.data
        and "__from" in message.data
        and isinstance(message.data["page"], list)
    )
    if not valid:
        if message.msg_type == "gui.page.show":
            action = "shown"
        else:
            action = "removed"
        LOG.error(
            f"Page will not be {action} due to malformed data in the"
            f"{message.msg_type} message"
        )

    return valid


def _get_idle_display_config():
    """Retrieves the current value of the idle display skill configuration."""
    LOG.info("Getting Idle Skill From Config")
    config = Configuration.get()
    enclosure_config = config.get("enclosure")
    idle_display_skill = enclosure_config.get("idle_display_skill")

    return idle_display_skill


class NamespaceManager:
    """Manages the active namespace stack and the content of namespaces.

    Attributes:
        core_bus: client for communicating with the core message bus
        gui_bus: client for communicating with the GUI message bus
        loaded_namespaces: cache of namespaces that have been introduced
        active_namespaces: LIFO stack of namespaces being displayed
        remove_namespace_timers: background process to remove a namespace with
            a persistence expressed in seconds
        idle_display_skill: skill ID of the skill that controls the idle screen
    """
    def __init__(self, core_bus: MessageBusClient):
        self.core_bus = core_bus
        self.gui_bus = create_gui_service(self)
        self.loaded_namespaces = dict()
        self.active_namespaces = list()
        self.remove_namespace_timers = dict()
        self.idle_display_skill = _get_idle_display_config()
        self._define_message_handlers()

    def _define_message_handlers(self):
        """Assigns methods as handlers for specified message types."""
        self.core_bus.on("gui.clear.namespace", self.handle_clear_namespace)
        self.core_bus.on("gui.event.send", self.handle_send_event)
        self.core_bus.on("gui.page.delete", self.handle_delete_page)
        self.core_bus.on("gui.page.show", self.handle_show_page)
        self.core_bus.on("gui.status.request", self.handle_status_request)
        self.core_bus.on("gui.value.set", self.handle_set_value)
        self.core_bus.on("mycroft.gui.connected", self.handle_client_connected)
        self.core_bus.on("gui.page_interaction", self.handle_page_interaction)

    def handle_clear_namespace(self, message: Message):
        """Handles a request to remove a namespace.

        Args:
            message: the message requesting namespace removal
        """
        try:
            namespace_name = message.data['__from']
        except KeyError:
            LOG.error(
                "Request to delete namespace failed: no namespace specified"
            )
        else:
            with namespace_lock:
                self._remove_namespace(namespace_name)

    @staticmethod
    def handle_send_event(message: Message):
        """Handles a request to send a message to the GUI message bus.

        Args:
            message: the message requesting a message to be sent to the GUI
                message bus.
        """
        try:
            message = dict(
                type='mycroft.events.triggered',
                namespace=message.data.get('__from'),
                event_name=message.data.get('event_name'),
                params=message.data.get('params')
            )
            send_message_to_gui(message)
        except Exception:
            LOG.exception('Could not send event trigger')

    def handle_delete_page(self, message: Message):
        """Handles request to remove one or more pages from a namespace.

        Args:
            message: the message requesting page removal
        """
        message_is_valid = _validate_page_message(message)
        if message_is_valid:
            namespace_name = message.data["__from"]
            pages_to_remove = message.data["page"]
            with namespace_lock:
                self._remove_pages(namespace_name, pages_to_remove)

    def _remove_pages(self, namespace_name: str, pages_to_remove: List[str]):
        """Removes one or more pages from a namespace.

        Pages are removed from the bottom of the stack.

        Args:
            namespace_name: the affected namespace
            pages_to_remove: names of pages to delete
        """
        namespace = self.loaded_namespaces.get(namespace_name)
        if namespace is not None and namespace in self.active_namespaces:
            page_positions = []
            for index, page in enumerate(pages_to_remove):
                if page in namespace.pages:
                    page_positions.append(index)
            page_positions.sort(reverse=True)
            namespace.remove_pages(page_positions)

    def handle_show_page(self, message: Message):
        """Handles a request to show one or more pages on the screen.

        Args:
            message: the message containing the page show request
        """
        LOG.info("Handling page show request")
        message_is_valid = _validate_page_message(message)
        if message_is_valid:
            namespace_name = message.data["__from"]
            pages_to_show = message.data["page"]
            persistence = message.data["__idle"]
            with namespace_lock:
                self._activate_namespace(namespace_name)
                self._load_pages(pages_to_show)
                self._update_namespace_persistence(persistence)

    def _activate_namespace(self, namespace_name: str):
        """Instructs the GUI to load a namespace and its associated data.

        Args:
            namespace_name: the name of the namespace to load
        """
        namespace = self._ensure_namespace_exists(namespace_name)
        if namespace in self.active_namespaces:
            namespace_position = self.active_namespaces.index(namespace)
            namespace.activate(namespace_position)
            self.active_namespaces.insert(
                0, self.active_namespaces.pop(namespace_position)
            )
        else:
            namespace.add()
            self.active_namespaces.insert(0, namespace)
        for key, value in namespace.data.items():
            namespace.load_data(key, value)

        self._emit_namespace_displayed_event()

    def _ensure_namespace_exists(self, namespace_name: str) -> Namespace:
        """Retrieves the requested namespace, creating one if it doesn't exist.

        Args:
            namespace_name: the name of the namespace being retrieved

        Returns:
            the requested namespace
        """
        # TODO: - Update sync to match.
        namespace = self.loaded_namespaces.get(namespace_name)
        if namespace is None:
            namespace = Namespace(namespace_name)
            self.loaded_namespaces[namespace_name] = namespace

        return namespace

    def _load_pages(self, pages_to_show: str):
        """Loads the requested pages in the namespace.

        Args:
            pages_to_show: the pages requested to be loaded
        """
        active_namespace = self.active_namespaces[0]
        active_namespace.load_pages(pages_to_show)

    def _update_namespace_persistence(self, persistence: Union[bool, int]):
        """Sets the persistence of the namespace being activated.

        A namespace's persistence is the same as the persistence of the
        most recent pages added to a namespace.  For example, a multi-page
        namespace could show the first set of pages with a persistence of
        True (show until removed) and the last page with a persistence of
        15 seconds.  This would ensure that the namespace isn't removed while
        the skill is showing the pages.

        Args:
            persistence: length of time the namespace should be displayed
        """
        LOG.debug("Setting namespace persistence to {}".format(persistence))
        for position, namespace in enumerate(self.active_namespaces):
            if position:
                if not namespace.persistent:
                    self._remove_namespace(namespace.name)
            else:
                if namespace.name == self.idle_display_skill:
                    namespace.set_persistence(True)
                else:
                    namespace.set_persistence(persistence)
                    
                    # check if there is a scheduled remove_namespace_timer and cancel it
                    if namespace.persistent:
                        if self.remove_namespace_timers[namespace.name]:
                            self.remove_namespace_timers[namespace.name].cancel()
                            self._del_namespace_in_remove_timers(namespace.name)
                                            
                if not namespace.persistent:
                    self._schedule_namespace_removal(namespace)

    def _schedule_namespace_removal(self, namespace: Namespace):
        """Uses a timer thread to remove the namespace.

        Args:
            namespace: the namespace to be removed
        """
        LOG.debug("Scheduling namespace removal")
        remove_namespace_timer = Timer(
            namespace.duration,
            self._remove_namespace_via_timer,
            args=(namespace.name,)
        )
        LOG.debug("Scheduled removal of namespace {} in duration {}".format(namespace.name, namespace.duration))
        remove_namespace_timer.start()
        self.remove_namespace_timers[namespace.name] = remove_namespace_timer

    def _remove_namespace_via_timer(self, namespace_name: str):
        """Removes a namespace and the corresponding timer instance."""
        self._remove_namespace(namespace_name)
        self._del_namespace_in_remove_timers(namespace_name)

    def _remove_namespace(self, namespace_name: str):
        """Removes a namespace from the active namespace stack.

        Args:
            namespace_name: namespace to remove
        """
        namespace = self.loaded_namespaces.get(namespace_name)
        if namespace is not None and namespace in self.active_namespaces:
            namespace_position = self.active_namespaces.index(namespace)
            namespace.remove(namespace_position)
            self.active_namespaces.remove(namespace)
        self._emit_namespace_displayed_event()

    def _emit_namespace_displayed_event(self):
        displaying_namespace = self.active_namespaces[0]
        message_data = dict(skill_id=displaying_namespace.name)
        self.core_bus.emit(
            Message("gui.namespace.displayed", data=message_data)
        )

    def handle_status_request(self, message: Message):
        """Handles a GUI status request by replying with the connection status.

        Args:
            message: the request for status of the GUI
        """
        gui_connected = determine_if_gui_connected()
        reply = message.reply(
            "gui.status.request.response", dict(connected=gui_connected)
        )
        self.core_bus.emit(reply)

    def handle_set_value(self, message: Message):
        """Handles a request to set the value of namespace data attributes.

        Args:
            message: the request to set attribute values
        """
        try:
            namespace_name = message.data['__from']
        except KeyError:
            LOG.error(
                "Request to set gui attribute value failed: no "
                "namespace specified"
            )
        else:
            with namespace_lock:
                self._update_namespace_data(namespace_name, message.data)

    def _update_namespace_data(self, namespace_name: str, data: dict):
        """Updates the values of namespace data attributes, unless unchanged.

        Args:
            namespace_name: the name of the namespace to update
            data: the name and new value of one or more data attributes
        """
        namespace = self._ensure_namespace_exists(namespace_name)
        for key, value in data.items():
            if key not in RESERVED_KEYS and namespace.data.get(key) != value:
                LOG.debug(f"Setting {key} to {value} in namespace {namespace.name}")
                namespace.data[key] = value
                if namespace in self.active_namespaces:
                    namespace.load_data(key, value)

    def handle_client_connected(self, message: Message):
        """Handles an event from the GUI indicating it is connected to the bus.

        Args:
            message: the event sent by the GUI
        """
        # GUI has announced presence
        # Announce connection, the GUI should connect on it soon
        gui_id = message.data.get("gui_id")
        LOG.info(f"GUI with ID {gui_id} connected to core message bus")
        websocket_config = get_gui_websocket_config()
        port = websocket_config["base_port"]
        message = Message("mycroft.gui.port", dict(port=port, gui_id=gui_id))
        self.core_bus.emit(message)

    def handle_page_interaction(self, message: Message):
        """Handles an event from the GUI indicating the page has been interacted with.
        
        Args:
            message: the event sent by the GUI
        """
        # GUI has interacted with a page
        # Update and increase the namespace duration and reset the remove timer
        namespace_name = message.data.get("skill_id")
        LOG.debug("GUI interacted with page in namespace {}".format(namespace_name))
        if namespace_name == self.idle_display_skill:
            return
        else: 
            namespace = self.loaded_namespaces.get(namespace_name)
            if not namespace.persistent:
                if self.remove_namespace_timers[namespace.name]:
                    LOG.debug("Resetting remove timer for namespace {}".format(namespace.name))
                    self.remove_namespace_timers[namespace.name].cancel()
                    self._del_namespace_in_remove_timers(namespace.name)
                    self._schedule_namespace_removal(namespace)
    
    def _del_namespace_in_remove_timers(self, namespace_name):
        """ Delete namespace from remove_namespace_timers dict.
        
        Args:
            namespace: namespace to be deleted
        """
        if namespace_name in self.remove_namespace_timers:
            del self.remove_namespace_timers[namespace_name]