# Copyright 2016 Mycroft AI, Inc.
#
# This file is part of Mycroft Core.
#
# Mycroft Core is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Mycroft Core is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Mycroft Core.  If not, see <http://www.gnu.org/licenses/>.


import subprocess
import sys
from threading import Thread, Lock
import re

from mycroft.client.speech.listener import RecognizerLoop
from mycroft.configuration import ConfigurationManager
from mycroft.messagebus.client.ws import WebsocketClient
from mycroft.messagebus.message import Message
from mycroft.tts import tts_factory
from mycroft.util.log import getLogger
from mycroft.util import kill, connected

logger = getLogger("SpeechClient")
client = None
tts = tts_factory.create()
mutex = Lock()
loop = None

config = ConfigurationManager.get()


def handle_record_begin():
    logger.info("Begin Recording...")
    client.emit(Message('recognizer_loop:record_begin'))


def handle_record_end():
    logger.info("End Recording...")
    client.emit(Message('recognizer_loop:record_end'))


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
        tts.execute(utterance, client)
    finally:
        loop.unmute()
        mutex.release()
        client.emit(Message("recognizer_loop:audio_output_end"))


def handle_multi_utterance_intent_failure(event):
    logger.info("Failed to find intent on multiple intents.")
    # TODO: Localize
    mute_and_speak("Sorry, I didn't catch that. Please rephrase your request.")


def handle_speak(event):
    utterance = event.metadata['utterance']
    chunks = re.split(r'(?<!\w\.\w.)(?<![A-Z][a-z]\.)(?<=\.|\?)\s', utterance)
    for chunk in chunks:
        mute_and_speak(chunk)


def handle_sleep(event):
    loop.sleep()


def handle_wake_up(event):
    loop.awaken()


def handle_stop(event):
    kill([config.get('tts').get('module')])


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
    loop.on('recognizer_loop:utterance', handle_utterance)
    loop.on('recognizer_loop:record_begin', handle_record_begin)
    loop.on('recognizer_loop:wakeword', handle_wakeword)
    loop.on('recognizer_loop:record_end', handle_record_end)
    loop.on('speak', handle_speak)
    client.on('speak', handle_speak)
    client.on(
        'multi_utterance_intent_failure',
        handle_multi_utterance_intent_failure)
    client.on('recognizer_loop:sleep', handle_sleep)
    client.on('recognizer_loop:wake_up', handle_wake_up)
    client.on('mycroft.stop', handle_stop)
    event_thread = Thread(target=connect)
    event_thread.setDaemon(True)
    event_thread.start()

    try:
        subprocess.call('echo "eyes.reset" >/dev/ttyAMA0', shell=True)
    except:
        pass

    try:
        loop.run()
    except KeyboardInterrupt, e:
        logger.exception(e)
        event_thread.exit()
        sys.exit()


if __name__ == "__main__":
    main()
