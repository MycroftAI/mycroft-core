Mycroft plugins
===============
Mycroft is extendable by plugins. These plugins can add support for new Speech To Text engines, Text To Speech engines, wake word engines and add new audio playback options.

TTS - Base for TTS plugins
--------------------------
.. autoclass:: mycroft.tts.TTS
    :members:

STT - base for STT plugins
--------------------------
.. autoclass:: mycroft.stt.STT
    :members:
|
|
.. autoclass:: mycroft.stt.StreamingSTT
    :members:
|
|
.. autoclass:: mycroft.stt.StreamThread
    :members:

HotWordEngine - Base for Hotword engine plugins
-----------------------------------------------
.. autoclass:: mycroft.client.speech.hotword_factory.HotWordEngine
    :members:

AudioBackend - Base for audioservice backend plugins
------------------
.. autoclass:: mycroft.audio.services.AudioBackend
    :members:
|
|
.. autoclass:: mycroft.audio.services.RemoteAudioBackend
    :members:

