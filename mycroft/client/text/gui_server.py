# Copyright 2018 Mycroft AI Inc.
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
from os.path import basename
import json
import websocket
from threading import Thread, Lock

from mycroft.messagebus.client import MessageBusClient
from mycroft.messagebus.message import Message


bus = None
buffer = None       # content will show on the CLI "GUI" representation
msgs = []

loaded = []
skill = None
page = None
vars = {}


def start_qml_gui(messagebus, output_buf):
    global bus
    global buffer

    bus = messagebus
    buffer = output_buf

    # Initiate the QML GUI
    log_message("Announcing CLI GUI")
    bus.on('mycroft.gui.port', handle_gui_ready)
    bus.emit(Message("mycroft.gui.connected",
                     {"gui_id": "cli_" + str(getpid())}))
    log_message("Announced CLI GUI")


def log_message(msg):
    global msgs
    msgs.append(msg)
    if len(msgs) > 20:
        del msgs[0]
    build_output_buffer()


def build_output_buffer():
    global buffer
    buffer.clear()
    try:
        if skill:
            buffer.append("Active Skill: {}".format(skill))
            buffer.append("Page: {}".format(basename(page)))
            buffer.append("vars: ")
            for v in vars[skill]:
                buffer.append("     {}: {}".format(v, vars[skill][v]))
    except Exception as e:
        buffer.append(repr(e))
    buffer.append("-----------------")
    buffer.append("MESSAGES")
    buffer.append("-----------------")
    for m in msgs:
        if len(buffer) > 20:    # cap out at 20 lines total
            return
        buffer.append(m)


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


def on_gui_message(ws, payload):
    global loaded
    global skill
    global page
    global vars
    try:
        msg = json.loads(payload)
        log_message("Msg: "+str(payload))
        type = msg.get("type")
        if type == "mycroft.session.set":
            skill = msg.get("namespace")
            data = msg.get("data")
            if skill not in vars:
                vars[skill] = {}
            for d in data:
                vars[skill][d] = data[d]
        elif type == "mycroft.session.list.insert":
            # Insert new namespace
            skill = msg.get('data')[0]['skill_id']
            loaded.insert(0, [skill, []])
        elif type == "mycroft.gui.list.insert":
            # Insert a page in an existing namespace
            page = msg['data'][0]['url']
            pos = msg.get('position')
            loaded[0][1].insert(pos, page)
            skill = loaded[0][0]
        elif type == "mycroft.session.list.move":
            # Move the namespace at "pos" to the top of the stack
            pos = msg.get('from')
            loaded.insert(0, loaded.pop(pos))
        elif type == "mycroft.events.triggered":
            # Switch selected page of namespace
            skill = msg['namespace']
            pos = msg['data']['number']
            for n in loaded:
                if n[0] == skill:
                    page = n[1][pos]

        build_output_buffer()
    except Exception as e:
        log_message(repr(e))
        log_message("Invalid JSON: "+str(payload))


def on_gui_close(ws):
    log_message("GUI closed")


def on_gui_error(ws, err):
    log_message("GUI error: "+str(err))
