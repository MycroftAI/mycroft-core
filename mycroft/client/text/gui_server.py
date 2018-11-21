# Copyright 2017 Mycroft AI Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

from os import getpid
import websocket
from threading import Thread, Lock

from mycroft.messagebus.client.ws import WebsocketClient
from mycroft.messagebus.message import Message


log_message = None
bus = None

def start_qml_gui(messagebus, debug_func):
    global log_message
    global bus

    bus = messagebus
    log_message = debug_func

    # Initiate the QML GUI
    log_message("Announcing CLI GUI")
    bus.on('mycroft.gui.port', handle_gui_ready)
    bus.emit(Message("mycroft.gui.connected",
                     {"gui_id" : "cli_" + str(getpid())}))

    log_message("Announced CLI GUI")


def handle_gui_ready(msg):
    # Attempt to connect to the port
    gui_id = msg.data.get("gui_id")
    if not gui_id == "cli_" + str(getpid()):
        # Not us, ignore!
        return

    # Create the websocket for GUI communications
    port = msg.data.get("port")
    if port:
        log_message("Connecting CLI GUI on "+str(port))
        #ws = create_connection("ws://0.0.0.0:" + str(port) + "/gui",
        ws = websocket.WebSocketApp("ws://0.0.0.0:" + str(port) + "/gui",
                               on_message=on_gui_message,
                               on_error=on_gui_error,
                               on_close=on_gui_close)

        log_message("WS = "+str(ws))
        event_thread = Thread(target=gui_connect, args=[ws])
        event_thread.setDaemon(True)
        event_thread.start()


def gui_connect(ws):
    # Once the websocket has connected, just watch it for speak events
    log_message("GUI Connected"+str(ws))
    ws.on_open = on_gui_open
    ws.run_forever()


def on_gui_open(ws):
    log_message("GUI Opened")


def on_gui_message(ws, msg):
    log_message("GUI msg: "+str(msg))


def on_gui_close(ws):
    log_message("GUI closed")


def on_gui_error(ws, err):
    log_message("GUI error: "+str(err))
