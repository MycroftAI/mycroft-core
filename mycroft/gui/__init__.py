# Copyright 2019 Mycroft AI Inc.
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
""" Interface for interacting with the Mycroft gui qml viewer. """
from os.path import join

from mycroft.configuration import Configuration
from mycroft.messagebus.message import Message
from mycroft.util import resolve_resource_file
from mycroft.util.log import LOG


class _GUIDict(dict):
    """ this is an helper dictionay subclass, it ensures that value changed
    in it are propagated to the GUI service real time"""

    def __init__(self, gui, **kwargs):
        self.gui = gui
        super().__init__(**kwargs)

    def __setitem__(self, key, value):
        super(_GUIDict, self).__setitem__(key, value)
        self.gui._sync_data()


class SkillGUI:
    """SkillGUI - Interface to the Graphical User Interface

    Values set in this class are synced to the GUI, accessible within QML
    via the built-in sessionData mechanism.  For example, in Python you can
    write in a skill:
        self.gui['temp'] = 33
        self.gui.show_page('Weather.qml')
    Then in the Weather.qml you'd access the temp via code such as:
        text: sessionData.time
    """

    def __init__(self, skill):
        self.__session_data = {}  # synced to GUI for use by this skill's pages
        self.pages = []
        self.current_page_idx = -1
        self.skill = skill
        self.on_gui_changed_callback = None
        self.config = Configuration.get()

    @property
    def bus(self):
        if self.skill:
            return self.skill.bus
        return None

    @property
    def connected(self):
        """Returns True if at least 1 gui is connected, else False"""
        if self.bus:
            reply = self.bus.wait_for_response(
                Message("gui.status.request"), "gui.status.request.response")
            if reply:
                return reply.data["connected"]
        return False

    @property
    def page(self):
        # the active GUI page (e.g. QML template) to show
        return self.pages[self.current_page_idx] if len(self.pages) else None

    @property
    def remote_url(self):
        """Returns configuration value for url of remote-server."""
        return self.config.get('remote-server')

    def build_message_type(self, event):
        """Builds a message matching the output from the enclosure."""
        return '{}.{}'.format(self.skill.skill_id, event)

    def setup_default_handlers(self):
        """Sets the handlers for the default messages."""
        msg_type = self.build_message_type('set')
        self.skill.add_event(msg_type, self.gui_set)

    def register_handler(self, event, handler):
        """Register a handler for GUI events.

        When using the triggerEvent method from Qt
        triggerEvent("event", {"data": "cool"})

        Args:
            event (str):    event to catch
            handler:        function to handle the event
        """
        msg_type = self.build_message_type(event)
        self.skill.add_event(msg_type, handler)

    def set_on_gui_changed(self, callback):
        """Registers a callback function to run when a value is
        changed from the GUI.

        Args:
            callback:   Function to call when a value is changed
        """
        self.on_gui_changed_callback = callback

    def gui_set(self, message):
        """Handler catching variable changes from the GUI.

        Args:
            message: Messagebus message
        """
        for key in message.data:
            self[key] = message.data[key]
        if self.on_gui_changed_callback:
            self.on_gui_changed_callback()

    def _sync_data(self):
        data = self.__session_data.copy()
        data.update({'__from': self.skill.skill_id})
        if self.bus:
            self.bus.emit(Message("gui.value.set", data))

    def __setitem__(self, key, value):
        """Implements set part of dict-like behaviour with named keys."""

        # cast to helper dict subclass that syncs data
        if isinstance(value, dict) and not isinstance(value, _GUIDict):
            value = _GUIDict(self, **value)

        self.__session_data[key] = value

        # emit notification (but not needed if page has not been shown yet)
        if self.page:
            self._sync_data()

    def __getitem__(self, key):
        """Implements get part of dict-like behaviour with named keys."""
        return self.__session_data[key]

    def get(self, *args, **kwargs):
        """Implements the get method for accessing dict keys."""
        return self.__session_data.get(*args, **kwargs)

    def __contains__(self, key):
        """Implements the "in" operation."""
        return self.__session_data.__contains__(key)

    def clear(self):
        """Reset the value dictionary, and remove namespace from GUI.

        This method does not close the GUI for a Skill. For this purpose see
        the `release` method.
        """
        self.__session_data = {}
        self.pages = []
        self.current_page_idx = -1
        if self.bus:
            self.bus.emit(Message("gui.clear.namespace",
                                  {"__from": self.skill.skill_id}))

    def send_event(self, event_name, params=None):
        """Trigger a gui event.

        Args:
            event_name (str): name of event to be triggered
            params: json serializable object containing any parameters that
                    should be sent along with the request.
        """
        params = params or {}
        if self.bus:
            self.bus.emit(Message("gui.event.send",
                                  {"__from": self.skill.skill_id,
                                   "event_name": event_name,
                                   "params": params}))

    def _pages2uri(self, page_names):
        # Convert pages to full reference
        page_urls = []
        for name in page_names:
            if name.startswith("SYSTEM"):
                page = resolve_resource_file(join('ui', name))
            else:
                page = self.skill.find_resource(name, 'ui')
            if page:
                if self.remote_url:
                    page_urls.append(self.remote_url + "/" + page)
                elif page.startswith("file://"):
                    page_urls.append(page)
                else:
                    page_urls.append("file://" + page)
            else:
                raise FileNotFoundError("Unable to find page: {}".format(name))

        return page_urls

    # base gui interactions
    def show_page(self, name, override_idle=None,
                  override_animations=False):
        """Begin showing the page in the GUI

        Args:
            name (str): Name of page (e.g "mypage.qml") to display
            override_idle (boolean, int):
                True: Takes over the resting page indefinitely
                (int): Delays resting page for the specified number of
                       seconds.
            override_animations (boolean):
                True: Disables showing all platform skill animations.
                False: 'Default' always show animations.
        """
        self.show_pages([name], 0, override_idle, override_animations)

    def show_pages(self, page_names, index=0, override_idle=None,
                   override_animations=False):
        """Begin showing the list of pages in the GUI.

        Args:
            page_names (list): List of page names (str) to display, such as
                               ["Weather.qml", "Forecast.qml", "Details.qml"]
            index (int): Page number (0-based) to show initially.  For the
                         above list a value of 1 would start on "Forecast.qml"
            override_idle (boolean, int):
                True: Takes over the resting page indefinitely
                (int): Delays resting page for the specified number of
                       seconds.
            override_animations (boolean):
                True: Disables showing all platform skill animations.
                False: 'Default' always show animations.
        """
        if isinstance(page_names, str):
            page_names = [page_names]
        if not isinstance(page_names, list):
            raise ValueError('page_names must be a list')

        if index > len(page_names):
            LOG.error('Default index is larger than page list length')
            index = len(page_names) - 1

        self.pages = page_names
        self.current_page_idx = index

        # First sync any data...
        data = self.__session_data.copy()
        data.update({'__from': self.skill.skill_id})
        if self.bus:
            self.bus.emit(Message("gui.value.set", data))

        # Convert pages to full reference
        page_urls = self._pages2uri(page_names)
        if self.bus:
            self.bus.emit(Message("gui.page.show",
                                  {"page": page_urls,
                                   "index": index,
                                   "__from": self.skill.skill_id,
                                   "__idle": override_idle,
                                   "__animations": override_animations}))

    def remove_page(self, page):
        """Remove a single page from the GUI.

        Args:
            page (str): Page to remove from the GUI
        """
        return self.remove_pages([page])

    def remove_pages(self, page_names):
        """Remove a list of pages in the GUI.

        Args:
            page_names (list): List of page names (str) to display, such as
                               ["Weather.qml", "Forecast.qml", "Other.qml"]
        """
        if not isinstance(page_names, list):
            page_names = [page_names]
        page_urls = self._pages2uri(page_names)
        if self.bus:
            self.bus.emit(Message("gui.page.delete",
                                  {"page": page_urls,
                                   "__from": self.skill.skill_id}))

    def show_text(self, text, title=None, override_idle=None,
                  override_animations=False):
        """Display a GUI page for viewing simple text.

        Args:
            text (str): Main text content.  It will auto-paginate
            title (str): A title to display above the text content.
            override_idle (boolean, int):
                True: Takes over the resting page indefinitely
                (int): Delays resting page for the specified number of
                       seconds.
            override_animations (boolean):
                True: Disables showing all platform skill animations.
                False: 'Default' always show animations.
        """
        self["text"] = text
        self["title"] = title
        self.show_page("SYSTEM_TextFrame.qml", override_idle,
                       override_animations)

    def show_image(self, url, caption=None,
                   title=None, fill=None,
                   override_idle=None, override_animations=False):
        """Display a GUI page for viewing an image.

        Args:
            url (str): Pointer to the image
            caption (str): A caption to show under the image
            title (str): A title to display above the image content
            fill (str): Fill type supports 'PreserveAspectFit',
            'PreserveAspectCrop', 'Stretch'
            override_idle (boolean, int):
                True: Takes over the resting page indefinitely
                (int): Delays resting page for the specified number of
                       seconds.
            override_animations (boolean):
                True: Disables showing all platform skill animations.
                False: 'Default' always show animations.
        """
        self["image"] = url
        self["title"] = title
        self["caption"] = caption
        self["fill"] = fill
        self.show_page("SYSTEM_ImageFrame.qml", override_idle,
                       override_animations)

    def show_animated_image(self, url, caption=None,
                            title=None, fill=None,
                            override_idle=None, override_animations=False):
        """Display a GUI page for viewing an image.

        Args:
            url (str): Pointer to the .gif image
            caption (str): A caption to show under the image
            title (str): A title to display above the image content
            fill (str): Fill type supports 'PreserveAspectFit',
            'PreserveAspectCrop', 'Stretch'
            override_idle (boolean, int):
                True: Takes over the resting page indefinitely
                (int): Delays resting page for the specified number of
                       seconds.
            override_animations (boolean):
                True: Disables showing all platform skill animations.
                False: 'Default' always show animations.
        """
        self["image"] = url
        self["title"] = title
        self["caption"] = caption
        self["fill"] = fill
        self.show_page("SYSTEM_AnimatedImageFrame.qml", override_idle,
                       override_animations)

    def show_html(self, html, resource_url=None, override_idle=None,
                  override_animations=False):
        """Display an HTML page in the GUI.

        Args:
            html (str): HTML text to display
            resource_url (str): Pointer to HTML resources
            override_idle (boolean, int):
                True: Takes over the resting page indefinitely
                (int): Delays resting page for the specified number of
                       seconds.
            override_animations (boolean):
                True: Disables showing all platform skill animations.
                False: 'Default' always show animations.
        """
        self["html"] = html
        self["resourceLocation"] = resource_url
        self.show_page("SYSTEM_HtmlFrame.qml", override_idle,
                       override_animations)

    def show_url(self, url, override_idle=None,
                 override_animations=False):
        """Display an HTML page in the GUI.

        Args:
            url (str): URL to render
            override_idle (boolean, int):
                True: Takes over the resting page indefinitely
                (int): Delays resting page for the specified number of
                       seconds.
            override_animations (boolean):
                True: Disables showing all platform skill animations.
                False: 'Default' always show animations.
        """
        self["url"] = url
        self.show_page("SYSTEM_UrlFrame.qml", override_idle,
                       override_animations)

    def release(self):
        """Signal that this skill is no longer using the GUI,
        allow different platforms to properly handle this event.
        Also calls self.clear() to reset the state variables
        Platforms can close the window or go back to previous page"""
        if self.bus:
            self.clear()
            self.bus.emit(Message("mycroft.gui.screen.close",
                                  {"skill_id": self.skill.skill_id}))

    def shutdown(self):
        """Shutdown gui interface.

        Clear pages loaded through this interface and remove the skill
        reference to make ref counting warning more precise.
        """
        self.release()
        self.skill = None
