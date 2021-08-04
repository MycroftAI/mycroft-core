# Copyright 2020 Mycroft AI Inc.
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
"""Tests for the Enclosure GUI interface."""

from unittest import TestCase, mock

from mycroft.enclosure.gui import SkillGUI
from mycroft.messagebus import Message
from mycroft.util.file_utils import resolve_resource_file


class TestSkillGUI(TestCase):
    def setUp(self):
        self.mock_skill = mock.Mock(name="Skill")
        self.mock_skill.skill_id = "fortytwo-skill"

        def find_resource(page, folder):
            return "/test/{}/{}".format(folder, page)

        self.mock_skill.find_resource = find_resource
        self.gui = SkillGUI(self.mock_skill)

    def test_show_page(self):
        self.gui.show_page("meaning.qml")
        sent_message = self.mock_skill.bus.emit.call_args_list[-1][0][0]
        self.assertEqual(sent_message.msg_type, "gui.page.show")
        self.assertEqual(sent_message.data["__from"], "fortytwo-skill")
        self.assertEqual(sent_message.data["page"], ["file:///test/ui/meaning.qml"])
        self.assertEqual(sent_message.data["__idle"], None)

    def test_show_page_idle_override(self):
        self.gui.show_page("meaning.qml", override_idle=60)

        sent_message = self.mock_skill.bus.emit.call_args_list[-1][0][0]
        self.assertEqual(sent_message.data["__idle"], 60)

    def test_show_pages(self):
        self.gui.show_pages(
            ["meaning.qml", "life.qml", "universe.qml", "everything.qml"]
        )

        sent_message = self.mock_skill.bus.emit.call_args_list[-1][0][0]

        expected_pages = [
            "file:///test/ui/meaning.qml",
            "file:///test/ui/life.qml",
            "file:///test/ui/universe.qml",
            "file:///test/ui/everything.qml",
        ]
        self.assertEqual(sent_message.data["page"], expected_pages)

    def test_remove_page(self):
        self.gui.remove_page("vogon_poetry.qml")
        sent_message = self.mock_skill.bus.emit.call_args_list[-1][0][0]

        self.assertEqual(sent_message.msg_type, "gui.page.delete")
        self.assertEqual(sent_message.data["__from"], "fortytwo-skill")
        expected_page = "file:///test/ui/vogon_poetry.qml"
        self.assertEqual(sent_message.data["page"], [expected_page])

    def test_show_image(self):
        self.gui.show_image("arthur_dent.jpg")

        sent_message = self.mock_skill.bus.emit.call_args_list[-1][0][0]
        page_path = resolve_resource_file("ui/SYSTEM_ImageFrame.qml")
        page_url = "file://{}".format(page_path)
        self.assertEqual(sent_message.data["page"], [page_url])
        self.assertEqual(self.gui["image"], "arthur_dent.jpg")

    def test_show_animated_image(self):
        self.gui.show_animated_image("dancing_zaphod.gif")

        sent_message = self.mock_skill.bus.emit.call_args_list[-1][0][0]
        page_path = resolve_resource_file("ui/SYSTEM_AnimatedImageFrame.qml")
        page_url = "file://{}".format(page_path)
        self.assertEqual(sent_message.data["page"], [page_url])
        self.assertEqual(self.gui["image"], "dancing_zaphod.gif")

    def test_show_url(self):
        page = "https://en.wikipedia.org/wiki/" "The_Hitchhiker%27s_Guide_to_the_Galaxy"
        self.gui.show_url(page)

        sent_message = self.mock_skill.bus.emit.call_args_list[-1][0][0]
        page_path = resolve_resource_file("ui/SYSTEM_UrlFrame.qml")
        page_url = "file://{}".format(page_path)
        self.assertEqual(sent_message.data["page"], [page_url])
        self.assertEqual(self.gui["url"], page)

    def test_show_html(self):
        html = "<html><head><title>This Page!</title></head></html>"
        self.gui.show_html(html)

        sent_message = self.mock_skill.bus.emit.call_args_list[-1][0][0]
        page_path = resolve_resource_file("ui/SYSTEM_HtmlFrame.qml")
        page_url = "file://{}".format(page_path)
        self.assertEqual(sent_message.data["page"], [page_url])
        self.assertEqual(self.gui["html"], html)

    def test_send_event(self):
        """Check that send_event sends message using the correct format."""
        params = "Not again"
        self.gui.send_event("not.again", params)
        sent_message = self.mock_skill.bus.emit.call_args_list[-1][0][0]
        self.assertEqual(sent_message.msg_type, "gui.event.send")
        self.assertEqual(sent_message.data["__from"], "fortytwo-skill")
        self.assertEqual(sent_message.data["params"], params)

    def test_on_gui_change_callback(self):
        """Check that the registered function gets called on message from gui."""
        result = False

        def callback():
            nonlocal result
            result = True

        self.gui.set_on_gui_changed(callback)
        self.gui.gui_set(Message("dummy"))
        self.assertTrue(result)

    def test_gui_set(self):
        """Assert that the gui can set gui variables."""
        vars_from_gui = {"meaning": 43, "no": 42}
        self.gui.gui_set(Message("dummy", data=vars_from_gui))
        self.assertEqual(self.gui["meaning"], 43)
        self.assertEqual(self.gui["no"], 42)

    def test_not_connected(self):
        response = Message("dummy", data={"connected": False})
        self.mock_skill.bus.wait_for_response.return_value = response
        self.assertFalse(self.gui.connected)

    def test_connected(self):
        response = Message("dummy", data={"connected": True})
        self.mock_skill.bus.wait_for_response.return_value = response
        self.assertTrue(self.gui.connected)

    def test_connected_no_response(self):
        """Ensure that a timeout response results in not connected."""
        response = None
        self.mock_skill.bus.wait_for_response.return_value = response
        self.assertFalse(self.gui.connected)

    def test_get(self):
        """Ensure the get method returns expected values."""
        self.gui["example"] = "value"
        self.assertEqual(self.gui.get("example"), "value")
        self.assertEqual(self.gui.get("nothing"), None)
        self.assertEqual(self.gui.get(0), None)
        self.gui[0] = "value"
        self.assertEqual(self.gui.get(0), "value")

    def test_clear(self):
        """Ensure that namespace is cleared."""
        self.gui["example"] = "value"
        self.assertEqual(self.gui.get("example"), "value")
        self.gui.clear()
        self.assertEqual(self.gui.get("example"), None)

    def test_release(self):
        """Ensure the correct method and data is sent to close a Skill."""
        self.gui.show_page("meaning.qml")
        self.gui.release()
        sent_message = self.mock_skill.bus.emit.call_args_list[-1][0][0]
        self.assertEqual(sent_message.msg_type, "mycroft.gui.screen.close")
        self.assertEqual(sent_message.data["skill_id"], "fortytwo-skill")

    def test_shutdown(self):
        """Ensure the GUI is cleared and Skill ref removed on shutdown."""
        self.gui["example"] = "value"
        self.gui.show_page("meaning.qml")
        self.assertEqual(self.gui.skill, self.mock_skill)
        self.gui.shutdown()
        self.assertEqual(self.gui.get("example"), None)
        self.assertEqual(self.gui.skill, None)
