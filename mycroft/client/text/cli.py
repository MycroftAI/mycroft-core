import sys
from threading import Thread, Lock

from mycroft.messagebus.client.ws import WebsocketClient
from mycroft.messagebus.message import Message
from mycroft.tts import tts_factory
from mycroft.util.log import getLogger

tts = tts_factory.create()
client = None
mutex = Lock()
logger = getLogger("CLIClient")


def handle_speak(event):
    mutex.acquire()
    client.emit(Message("recognizer_loop:audio_output_start"))
    try:
        utterance = event.metadata.get('utterance')
        logger.info("Speak: " + utterance)
        tts.execute(utterance)
    finally:
        mutex.release()
        client.emit(Message("recognizer_loop:audio_output_end"))


def connect():
    client.run_forever()


def main():
    global client
    client = WebsocketClient()
    if '--quiet' not in sys.argv:
        client.on('speak', handle_speak)
    event_thread = Thread(target=connect)
    event_thread.setDaemon(True)
    event_thread.start()
    try:
        while True:
            print("Input:")
            line = sys.stdin.readline()
            client.emit(
                Message("recognizer_loop:utterance",
                        metadata={'utterances': [line.strip()]}))
    except KeyboardInterrupt, e:
        event_thread.exit()
        sys.exit()


if __name__ == "__main__":
    main()
