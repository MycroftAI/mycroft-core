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


import sys
import time
from threading import Thread, Lock

from mycroft.messagebus.client.ws import WebsocketClient
from mycroft.messagebus.message import Message
from mycroft.tts import TTSFactory
from mycroft.util.log import getLogger

tts = TTSFactory.create()
ws = None
mutex = Lock()
logger = getLogger("CLIClient")


def handle_speak(event):
    mutex.acquire()
    ws.emit(Message("recognizer_loop:audio_output_start"))
    try:
        utterance = event.data.get('utterance')
        print(">> " + utterance)
        tts.execute(utterance)
    finally:
        mutex.release()
        ws.emit(Message("recognizer_loop:audio_output_end"))


def handle_quiet(event):
    try:
        utterance = event.data.get('utterance')
        print(">> " + utterance)
    finally:
        pass


def connect():
    ws.run_forever()


def main():
    global ws
    ws = WebsocketClient()
    tts.init(ws)
    if '--quiet' in sys.argv:
        ws.on('speak', handle_quiet)
    else:
        ws.on('speak', handle_speak)
    event_thread = Thread(target=connect)
    event_thread.setDaemon(True)
    event_thread.start()
    try:
        while True:
            # TODO: Change this mechanism
            # Sleep for a while so all the output that results
            # from the previous command finishes before we print.
            time.sleep(1.5)
            print("Input (Ctrl+C to quit):")
            line = sys.stdin.readline()
            ws.emit(
                Message("recognizer_loop:utterance",
                        {'utterances': [line.strip()]}))
    except KeyboardInterrupt, e:
        # User hit Ctrl+C to quit
        print("")
    except KeyboardInterrupt, e:
        logger.exception(e)
        event_thread.exit()
        sys.exit()


if __name__ == "__main__":
    main()
