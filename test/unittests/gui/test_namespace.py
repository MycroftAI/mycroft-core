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
"""Tests for the GUI namespace helper class."""

from unittest import TestCase, mock

from mycroft.gui.namespace import Namespace
from mycroft.gui.page import GuiPage

PATCH_MODULE = "mycroft.gui.namespace"


class TestNamespace(TestCase):
    def setUp(self):
        self.namespace = Namespace("foo")

    def test_add(self):
        add_namespace_message = dict(
            type="mycroft.session.list.insert",
            namespace="mycroft.system.active_skills",
            position=0,
            data=[dict(skill_id="foo")]
        )
        patch_function = PATCH_MODULE + ".send_message_to_gui"
        with mock.patch(patch_function) as send_message_mock:
            self.namespace.add()
            send_message_mock.assert_called_with(add_namespace_message)

    def test_activate(self):
        activate_namespace_message = {
            "type": "mycroft.session.list.move",
            "namespace": "mycroft.system.active_skills",
            "from": 5,
            "to": 0,
            "items_number": 1
        }
        patch_function = PATCH_MODULE + ".send_message_to_gui"
        with mock.patch(patch_function) as send_message_mock:
            self.namespace.activate(position=5)
            send_message_mock.assert_called_with(activate_namespace_message)

    def test_remove(self):
        self.namespace.data = dict(foo="bar")
        self.namespace.pages = ["foo", "bar"]
        remove_namespace_message = dict(
            type="mycroft.session.list.remove",
            namespace="mycroft.system.active_skills",
            position=3,
            items_number=1
        )
        patch_function = PATCH_MODULE + ".send_message_to_gui"
        with mock.patch(patch_function) as send_message_mock:
            self.namespace.remove(position=3)
            send_message_mock.assert_called_with(remove_namespace_message)

        self.assertFalse(self.namespace.data)
        self.assertFalse(self.namespace.pages)

    def test_load_data(self):
        load_data_message = dict(
            type="mycroft.session.set",
            namespace="foo",
            data=dict(foo="bar")
        )
        patch_function = PATCH_MODULE + ".send_message_to_gui"
        with mock.patch(patch_function) as send_message_mock:
            self.namespace.load_data(name="foo", value="bar")
            send_message_mock.assert_called_with(load_data_message)

    def test_set_persistence_numeric(self):
        self.namespace.set_persistence("genericSkill")
        self.assertEqual(self.namespace.duration, 30)
        self.assertFalse(self.namespace.persistent)

    def test_set_persistence_boolean(self):
        self.namespace.set_persistence("idleDisplaySkill")
        self.assertEqual(self.namespace.duration, 0)
        self.assertTrue(self.namespace.persistent)

    def test_load_new_pages(self):
        self.namespace.pages = [GuiPage("foo", "foo.qml", True, 0), GuiPage("bar", "bar.qml", False, 30)]
        new_pages = [GuiPage("foobar", "foobar.qml", False, 30)]
        load_page_message = dict(
            type="mycroft.events.triggered",
            namespace="foo",
            event_name="page_gained_focus",
            data=dict(number=2)
        )
        patch_function = PATCH_MODULE + ".send_message_to_gui"
        with mock.patch(patch_function) as send_message_mock:
            self.namespace.load_pages(new_pages)
            send_message_mock.assert_called_with(load_page_message)
        self.assertListEqual(self.namespace.pages, self.namespace.pages)

    def test_load_existing_pages(self):
        self.namespace.pages = [GuiPage("foo", "foo.qml", True, 0), GuiPage("bar", "bar.qml", False, 30)]
        new_pages = [GuiPage("foo", "foo.qml", True, 0)]
        load_page_message = dict(
            type="mycroft.events.triggered",
            namespace="foo",
            event_name="page_gained_focus",
            data=dict(number=0)
        )
        patch_function = PATCH_MODULE + ".send_message_to_gui"
        with mock.patch(patch_function) as send_message_mock:
            self.namespace.load_pages(new_pages)
            send_message_mock.assert_called_with(load_page_message)
        self.assertListEqual(self.namespace.pages, self.namespace.pages)

    def test_remove_pages(self):
        self.namespace.pages = ["foo", "bar", "foobar"]
        remove_page_message = dict(
            type="mycroft.gui.list.remove",
            namespace="foo",
            position=2,
            items_number=1
        )
        patch_function = PATCH_MODULE + ".send_message_to_gui"
        with mock.patch(patch_function) as send_message_mock:
            self.namespace.remove_pages([2])
            send_message_mock.assert_called_with(remove_page_message)
        self.assertListEqual(["foo", "bar"], self.namespace.pages)
