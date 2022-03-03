from ovos_plugin_manager.stt import find_stt_plugins
from ovos_plugin_manager.tts import find_tts_plugins
from ovos_plugin_manager.wakewords import find_wake_word_plugins
from ovos_plugin_manager.audio import find_audio_service_plugins

from unittest import TestCase, mock


class TestFindDefaults(TestCase):
    def test_ww(self):
        expected = ["ovos-ww-plugin-pocketsphinx",
                    "ovos-ww-plugin-precise",
                    "ovos-precise-lite"  # TODO rename for convention
                    ]
        plugs = set(find_wake_word_plugins())
        for plug in expected:
            self.assertIn(plug, plugs)

    def test_stt(self):
        expected = ["ovos-stt-plugin-chromium",
                    "ovos-stt-plugin-vosk",
                    "ovos-stt-plugin-vosk-streaming"
                    ]
        plugs = set(find_stt_plugins())
        for plug in expected:
            self.assertIn(plug, plugs)

    def test_tts(self):
        expected = ["ovos-tts-plugin-mimic",
                    "ovos-tts-plugin-mimic2",
                    "ovos-tts-plugin-responsivevoice",
                    "ovos-tts-plugin-google-tx"
                    ]
        plugs = set(find_tts_plugins())
        for plug in expected:
            self.assertIn(plug, plugs)

    def test_audio(self):
        # TODO rename plugins for convention
        expected = ['ovos_common_play',
                    'ovos_audio_simple']
        plugs = set(find_audio_service_plugins())
        for plug in expected:
            self.assertIn(plug, plugs)