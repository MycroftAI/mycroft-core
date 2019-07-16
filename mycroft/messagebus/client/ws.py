# WebSocketClient has been deprecated in favor of the new MessageBusClient
# This is a backport for any skills using the message bus client.

# TODO: remove as part of 19.08
from .client import MessageBusClient


class WebSocketClient(MessageBusClient):
    pass
