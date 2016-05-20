import json

from mycroft.messagebus.client.ws import WebsocketClient
from mycroft.skills.core import load_skills
from mycroft.util.log import getLogger
logger = getLogger("Skills")

__author__ = 'seanfitz'

client = None


def load_skills_callback():
    global client
    load_skills(client)


def connect():
    global client
    client.run_forever()


def main():
    global client
    client = WebsocketClient()

    def echo(message):
        try:
            _message = json.loads(message)

            if _message.get("message_type") == "registration":
                # do not log tokens from registration messages
                _message["metadata"]["token"] = None
            message = json.dumps(_message)
        except:
            pass
        logger.debug(message)

    client.on('message', echo)
    client.once('open', load_skills_callback)
    client.run_forever()


if __name__ == "__main__":
    main()
