import unittest
import mycroft.tts


class TestSTT(unittest.TestCase):
    def test_ssml_support(self):
        class TestTTS(mycroft.tts.TTS):
            def execute(self, audio, language=None):
                pass

        class TestTTSValidator(mycroft.tts.TTSValidator):
            def validate(self):
                pass

        sentence = "<speak>Prosody can be used to change the way words " \
                   "sound. The following words are " \
                   "<prosody volume='x-loud'> " \
                   "quite a bit louder than the rest of this passage. " \
                   "</prosody> Each morning when I wake up, " \
                   "<prosody rate='x-slow'>I speak quite slowly and " \
                   "deliberately until I have my coffee.</prosody> I can " \
                   "also change the pitch of my voice using prosody. " \
                   "Do you like <prosody pitch='+5%'> speech with a pitch " \
                   "that is higher, </prosody> or <prosody pitch='-10%'> " \
                   "is a lower pitch preferable?</prosody></speak>"
        sentence_no_ssml = "Prosody can be used to change the way " \
                           "words sound. The following words are quite " \
                           "a bit louder than the rest of this passage. " \
                           "Each morning when I wake up, I speak quite " \
                           "slowly and deliberately until I have my " \
                           "coffee. I can also change the pitch of my " \
                           "voice using prosody. Do you like speech " \
                           "with a pitch that is higher, or is " \
                           "a lower pitch preferable?"
        sentence_bad_ssml = "<foo_invalid>" + sentence + \
                            "</foo_invalid end=whatever>"
        sentence_extra_ssml = "<whispered>whisper tts<\whispered>"

        # test valid ssml
        test_config = {'voice': 'test_voice', 'ssml': True}
        tts = TestTTS("en-US", test_config, TestTTSValidator(None))
        self.assertEqual(tts.validate_ssml(sentence), sentence)

        # test extra ssml
        test_config = {'voice': 'test_voice', 'ssml': True,
                       "extra_tags": ["whispered"]}
        tts = TestTTS("en-US", test_config, TestTTSValidator(None))
        self.assertEqual(tts.validate_ssml(sentence_extra_ssml),
                         sentence_extra_ssml)

        # test unsupported extra ssml
        test_config = {'voice': 'test_voice', 'ssml': True}
        tts = TestTTS("en-US", test_config, TestTTSValidator(None))
        self.assertEqual(tts.validate_ssml(sentence_extra_ssml), "whisper "
                                                                 "tts")

        # test mixed valid / invalid ssml
        test_config = {'voice': 'test_voice', 'ssml': True}
        tts = TestTTS("en-US", test_config, TestTTSValidator(None))
        self.assertEqual(tts.validate_ssml(sentence_bad_ssml), sentence)

        # test unsupported ssml
        test_config = {'voice': 'test_voice', 'ssml': False}
        tts = TestTTS("en-US", test_config, TestTTSValidator(None))
        self.assertEqual(tts.validate_ssml(sentence), sentence_no_ssml)

        self.assertEqual(tts.validate_ssml(sentence_bad_ssml),
                         sentence_no_ssml)
