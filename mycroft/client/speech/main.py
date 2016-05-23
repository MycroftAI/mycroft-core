import sys
from threading import Thread, Lock

from mycroft.client.speech.listener import RecognizerLoop
from mycroft.configuration.config import ConfigurationManager
from mycroft.messagebus.client.ws import WebsocketClient
from mycroft.messagebus.message import Message
from mycroft.tts import tts_factory
from mycroft.util.log import getLogger

logger = getLogger("SpeechClient")
client = None
tts = tts_factory.create()
mutex = Lock()
loop = None

config = ConfigurationManager.get_config()


def handle_listening():
    logger.info("Listening...")
    client.emit(Message('recognizer_loop:listening'))


def handle_wakeword(event):
    logger.info("Wakeword Detected: " + event['utterance'])
    client.emit(Message('recognizer_loop:wakeword', event))


def handle_utterance(event):
    logger.info("Utterance: " + str(event['utterances']))
    client.emit(Message('recognizer_loop:utterance', event))


def mute_and_speak(utterance):
    mutex.acquire()
    client.emit(Message("recognizer_loop:audio_output_start"))
    try:
        logger.info("Speak: " + utterance)
        loop.mute()
        tts.execute(utterance)
    finally:
        loop.unmute()
        mutex.release()
        client.emit(Message("recognizer_loop:audio_output_end"))


def handle_multi_utterance_intent_failure(event):
    logger.info("Failed to find intent on multiple intents.")
    # TODO: Localize
    mute_and_speak("Sorry, I didn't catch that. Please rephrase your request.")


def handle_speak(event):
    mute_and_speak(event.metadata['utterance'])


def handle_sleep(event):
    loop.sleep()


def handle_wake_up(event):
    loop.awaken()


def connect():
    client.run_forever()


def main():
    global client
    global loop
    client = WebsocketClient()
    device_index = config.get('speech_client').get('device_index')
    if device_index:
        device_index = int(device_index)
    loop = RecognizerLoop(device_index=device_index)
    loop.on('recognizer_loop:listening', handle_listening)
    loop.on('recognizer_loop:wakeword', handle_wakeword)
    loop.on('recognizer_loop:utterance', handle_utterance)
    loop.on('speak', handle_speak)
    client.on('speak', handle_speak)
    client.on(
        'multi_utterance_intent_failure',
        handle_multi_utterance_intent_failure)
    client.on('recognizer_loop:sleep', handle_sleep)
    client.on('recognizer_loop:wake_up', handle_wake_up)
    event_thread = Thread(target=connect)
    event_thread.setDaemon(True)
    event_thread.start()
    try:
        loop.run()
    except KeyboardInterrupt, e:
        event_thread.exit()
        sys.exit()


if __name__ == "__main__":
    main()
