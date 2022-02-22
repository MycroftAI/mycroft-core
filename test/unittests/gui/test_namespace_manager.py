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
"""Tests for the GUI namespace manager helper class."""

from unittest import TestCase, mock

from mycroft.gui.namespace import Namespace, NamespaceManager
from mycroft.gui.page import GuiPage
from mycroft.messagebus import Message
from ..mocks import MessageBusMock

PATCH_MODULE = "mycroft.gui.namespace"


class TestNamespace(TestCase):
    def setUp(self):
        with mock.patch(PATCH_MODULE + ".create_gui_service"):
            self.namespace_manager = NamespaceManager(MessageBusMock())

    def test_handle_clear_active_namespace(self):
        namespace = Namespace("foo")
        namespace.remove = mock.Mock()
        self.namespace_manager.loaded_namespaces = dict(foo=namespace)
        self.namespace_manager.active_namespaces = [namespace]

        message = Message("gui.clear.namespace", data={"__from": "foo"})
        self.namespace_manager.handle_clear_namespace(message)
        namespace.remove.assert_called_with(0)

    def test_handle_clear_inactive_namespace(self):
        message = Message("gui.clear.namespace", data={"__from": "foo"})
        namespace = Namespace("foo")
        namespace.remove = mock.Mock()
        self.namespace_manager.handle_clear_namespace(message)
        namespace.remove.assert_not_called()

    def test_handle_send_event(self):
        message_data = {
            "__from": "foo", "event_name": "bar", "params": "foobar"
        }
        message = Message("gui.clear.namespace", data=message_data)
        event_triggered_message = dict(
            type='mycroft.events.triggered',
            namespace="foo",
            event_name="bar",
            params="foobar"
        )
        patch_function = PATCH_MODULE + ".send_message_to_gui"
        with mock.patch(patch_function) as send_message_mock:
            self.namespace_manager.handle_send_event(message)
            send_message_mock.assert_called_with(event_triggered_message)

    def test_handle_delete_active_namespace_page(self):
        namespace = Namespace("foo")
        namespace.pages = [GuiPage("bar", "bar.qml", True, 0)]
        namespace.remove_pages = mock.Mock()
        self.namespace_manager.loaded_namespaces = dict(foo=namespace)
        self.namespace_manager.active_namespaces = [namespace]

        message_data = {"__from": "foo", "page": ["bar"]}
        message = Message("gui.clear.namespace", data=message_data)
        self.namespace_manager.handle_delete_page(message)
        namespace.remove_pages.assert_called_with([0])

    def test_handle_delete_inactive_namespace_page(self):
        namespace = Namespace("foo")
        namespace.pages = ["bar"]
        namespace.remove_pages = mock.Mock()

        message_data = {"__from": "foo", "page": ["bar"]}
        message = Message("gui.clear.namespace", data=message_data)
        self.namespace_manager.handle_delete_page(message)
        namespace.remove_pages.assert_not_called()

    def test_handle_show_pages(self):
        message_data = {"__from": "foo", "__idle": 10, "page": ["bar"]}
        message = Message("gui.page.show", data=message_data)
        patch_function = PATCH_MODULE + ".send_message_to_gui"
        with mock.patch(patch_function):
            self.namespace_manager._schedule_namespace_removal = mock.Mock()
            self.namespace_manager.handle_show_page(message)

        self.assertEqual(
            "foo", self.namespace_manager.active_namespaces[0].name
        )
        self.assertTrue("foo" in self.namespace_manager.loaded_namespaces)
        namespace = self.namespace_manager.loaded_namespaces["foo"]
        self.assertListEqual(namespace.pages, namespace.pages)

    def test_handle_show_pages_invalid_message(self):
        namespace = Namespace("foo")
        namespace.load_pages = mock.Mock()

        message_data = {"__from": "foo"}
        message = Message("gui.page.show", data=message_data)
        patch_function = PATCH_MODULE + ".send_message_to_gui"
        with mock.patch(patch_function):
            self.namespace_manager.handle_show_page(message)

        self.assertListEqual([], self.namespace_manager.active_namespaces)
        self.assertDictEqual({}, self.namespace_manager.loaded_namespaces)
