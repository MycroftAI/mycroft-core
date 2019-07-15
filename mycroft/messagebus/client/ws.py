# WebSocketClient has been deprecated in favor of the new MessageBusClient
# This is a backport for any skills using the message bus client.

# TODO: remove as part of 19.08
from mycroft.util.log import LOG
from .client import MessageBusClient


class WebsocketClient(MessageBusClient):
    def __init__(self):
        super().__init__()
        LOG.warning(
            "WebsocketClient is deprecated, use MessageBusClient instead"
        )
