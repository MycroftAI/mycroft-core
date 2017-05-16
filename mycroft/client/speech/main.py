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


import re
import sys
from threading import Thread, Lock
import time

from mycroft.client.enclosure.api import EnclosureAPI
from mycroft.client.speech.listener import RecognizerLoop
from mycroft.configuration import ConfigurationManager
from mycroft.identity import IdentityManager
from mycroft.messagebus.client.ws import WebsocketClient
from mycroft.messagebus.message import Message
from mycroft.tts import TTSFactory
from mycroft.util import kill, create_signal, check_for_signal
from mycroft.util.log import getLogger
from mycroft.lock import Lock as PIDLock  # Create/Support PID locking file

logger = getLogger("SpeechClient")
ws = None
tts = TTSFactory.create()
lock = Lock()
loop = None
_last_stop_signal = 0

config = ConfigurationManager.get()


def handle_record_begin():
    logger.info("Begin Recording...")
    ws.emit(Message('recognizer_loop:record_begin'))


def handle_record_end():
    logger.info("End Recording...")
    ws.emit(Message('recognizer_loop:record_end'))


def handle_no_internet():
    logger.debug("Notifying enclosure of no internet connection")
    ws.emit(Message('enclosure.notify.no_internet'))


def handle_wakeword(event):
    logger.info("Wakeword Detected: " + event['utterance'])
    ws.emit(Message('recognizer_loop:wakeword', event))


def handle_utterance(event):
    logger.info("Utterance: " + str(event['utterances']))
    ws.emit(Message('recognizer_loop:utterance', event))


def mute_and_speak(utterance):
    lock.acquire()
    ws.emit(Message("recognizer_loop:audio_output_start"))
    try:
        logger.info("Speak: " + utterance)
        loop.mute()
        tts.execute(utterance)
    finally:
        loop.unmute()
        lock.release()
        ws.emit(Message("recognizer_loop:audio_output_end"))


def handle_multi_utterance_intent_failure(event):
    logger.info("Failed to find intent on multiple intents.")
    # TODO: Localize
    mute_and_speak("Sorry, I didn't catch that. Please rephrase your request.")


def handle_speak(event):
    global _last_stop_signal

    utterance = event.data['utterance']
    expect_response = event.data.get('expect_response', False)

    # This is a bit of a hack for Picroft.  The analog audio on a Pi blocks
    # for 30 seconds fairly often, so we don't want to break on periods
    # (decreasing the chance of encountering the block).  But we will
    # keep the split for non-Picroft installs since it give user feedback
    # faster on longer phrases.
    #
    # TODO: Remove or make an option?  This is really a hack, anyway,
    # so we likely will want to get rid of this when not running on Mimic
    if not config.get('enclosure', {}).get('platform') == "picroft":
        start = time.time()
        chunks = re.split(r'(?<!\w\.\w.)(?<![A-Z][a-z]\.)(?<=\.|\?)\s',
                          utterance)
        for chunk in chunks:
            try:
                mute_and_speak(chunk)
            except:
                logger.error('Error in mute_and_speak', exc_info=True)
            if _last_stop_signal > start or check_for_signal('buttonPress'):
                break
    else:
        mute_and_speak(utterance)

    if expect_response:
        create_signal('startListening')


def handle_sleep(event):
    loop.sleep()


def handle_wake_up(event):
    loop.awaken()


def handle_stop(event):
    global _last_stop_signal
    _last_stop_signal = time.time()
    kill([config.get('tts').get('module')])
    kill(["aplay"])


def handle_paired(event):
    IdentityManager.update(event.data)


def handle_open():
    # Reset the UI to indicate ready for speech processing
    EnclosureAPI(ws).reset()


def connect():
    ws.run_forever()


def main():
    global ws
    global loop
    lock = PIDLock("voice")
    ws = WebsocketClient()
    tts.init(ws)
    ConfigurationManager.init(ws)
    loop = RecognizerLoop()
    loop.on('recognizer_loop:utterance', handle_utterance)
    loop.on('recognizer_loop:record_begin', handle_record_begin)
    loop.on('recognizer_loop:wakeword', handle_wakeword)
    loop.on('recognizer_loop:record_end', handle_record_end)
    loop.on('speak', handle_speak)
    loop.on('recognizer_loop:no_internet', handle_no_internet)
    ws.on('open', handle_open)
    ws.on('speak', handle_speak)
    ws.on(
        'multi_utterance_intent_failure',
        handle_multi_utterance_intent_failure)
    ws.on('recognizer_loop:sleep', handle_sleep)
    ws.on('recognizer_loop:wake_up', handle_wake_up)
    ws.on('mycroft.stop', handle_stop)
    ws.on("mycroft.paired", handle_paired)
    event_thread = Thread(target=connect)
    event_thread.setDaemon(True)
    event_thread.start()

    try:
        loop.run()
    except KeyboardInterrupt, e:
        logger.exception(e)
        event_thread.exit()
        sys.exit()


if __name__ == "__main__":
    main()
