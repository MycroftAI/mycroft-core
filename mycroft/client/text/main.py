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
import subprocess
from cStringIO import StringIO
from threading import Thread, Lock

import curses
import curses.ascii

from mycroft.messagebus.client.ws import WebsocketClient
from mycroft.messagebus.message import Message
from mycroft.tts import TTSFactory
from mycroft.util.log import getLogger

tts = None
ws = None
mutex = Lock()
logger = getLogger("CLIClient")

utterances = []
chat = []
mergedLog = []
line = "What time is it"
bQuiet = '--quiet' in sys.argv
scr = None

##############################################################################
# Helper functions

def clamp(n, smallest, largest):
    return max(smallest, min(n, largest))


def stripNonAscii(text):
    return ''.join([i if ord(i) < 128 else ' ' for i in text])


##############################################################################
# Log file monitoring

class LogMonitorThread(Thread):
    def __init__(self, filename):
        Thread.__init__(self)
        self.filename = filename

    def run(self):
        global mergedLog
        
        proc = subprocess.Popen(["tail", "-f", self.filename],
            stdout=subprocess.PIPE)
        while True:
            output = proc.stdout.readline().strip()
            if output == "" and proc.poll() is not None:
                break
            
            # TODO: Filter log output (black and white listing lines)
            if "enclosure.mouth.viseme" in output:
                continue
            
            if output:
                mergedLog.append(output)
                draw_screen()


def startLogMonitor(filename):
    thread = LogMonitorThread(filename)
    thread.setDaemon(True)  # this thread won't prevent prog from exiting
    thread.start()
  
  
##############################################################################
# Capturing output from Mycroft

def handle_speak(event):
    global chat
    mutex.acquire()
    if not bQuiet:
        ws.emit(Message("recognizer_loop:audio_output_start"))
    try:
        utterance = event.data.get('utterance')
        chat.append(">> " + utterance)
        draw_screen()
        if not bQuiet:
            if not tts:
                tts = TTSFactory.create()
                tts.init(ws)
            tts.execute(utterance)
    finally:
        mutex.release()
        if not bQuiet:
            ws.emit(Message("recognizer_loop:audio_output_end"))


def connect():
    # Once the websocket has connected, just watch it for speak events
    ws.run_forever()

##############################################################################
# Screen handling

def init_screen():
    global CLR_CHAT_HEADING
    global CLR_CHAT_RESP
    global CLR_CHAT_QUERY
    global CLR_CMDLINE
    global CLR_INPUT
    global CLR_LOG
    global CLR_LOG_DEBUG
    
    if curses.has_colors():
        bg = curses.COLOR_BLACK
        for i in range(0, curses.COLORS):
            curses.init_pair(i + 1, i, bg)

        # Colors
        # 1 = black on black
        # 2 = dk red
        # 3 = dk green
        # 4 = dk yellow
        # 5 = dk blue
        # 6 = dk purple
        # 7 = dk cyan
        # 8 = lt gray
        # 9 = dk gray
        # 10= red
        # 11= green
        # 12= yellow
        # 13= blue
        # 14= purple
        # 15= cyan
        # 16= white
 
        CLR_CHAT_HEADING = curses.color_pair(3)
        CLR_CHAT_RESP = curses.color_pair(7)
        CLR_CHAT_QUERY = curses.color_pair(8)
        CLR_CMDLINE = curses.color_pair(15)
        CLR_INPUT = curses.color_pair(16)
        CLR_LOG = curses.color_pair(8)
        CLR_LOG_DEBUG = curses.color_pair(4)

def draw_screen():
    global scr
    scr.clear()
    
    # Display log output at the top
    scr.addstr(0, 0, "Log Output", curses.A_REVERSE)
    scr.addstr(1, 0,  "=" * (curses.COLS-1), CLR_LOG)
    cLogLines = curses.LINES-13
 
    cLogs = len(mergedLog)
    y = 2
    for i in range(clamp(cLogs-cLogLines, 0, cLogs-1), cLogs):
        log = mergedLog[i]
        log = log[26:]  # skip date/time at the front of log line

        # Categorize log line
        if "Skills - DEBUG - " in log:
            log = log.replace("Skills - DEBUG - ", "")
            clr = CLR_LOG_DEBUG
        else:
            clr = CLR_LOG

        # limit line to screen width (show tail end)
        log = ("..."+log[-(curses.COLS-3):]) if len(log) > curses.COLS else log
        scr.addstr(y, 0, log, clr)
        y += 1
        
    # Log legend in the lower-right
    scr.addstr(curses.LINES-10, curses.COLS/2 + 2, "Log Output Legend", curses.A_REVERSE)
    scr.addstr(curses.LINES-9, curses.COLS/2 + 2, "=" * (curses.COLS/2 - 4))
    scr.addstr(curses.LINES-8, curses.COLS/2 + 2, "mycroft-skills.log, debug info", CLR_LOG_DEBUG)
    scr.addstr(curses.LINES-7, curses.COLS/2 + 2, "mycroft-skills.log, non debug", CLR_LOG)
    scr.addstr(curses.LINES-6, curses.COLS/2 + 2, "mycroft-voice.log", CLR_LOG)

    # History log in the middle
    scr.addstr(curses.LINES-10, 0, "History", CLR_CHAT_HEADING)
    scr.addstr(curses.LINES-9, 0,  "=" * (curses.COLS/2), CLR_CHAT_HEADING)

    cChat = len(chat)
    if cChat:
        y = curses.LINES-8
        for i in range(cChat-clamp(cChat, 1,5), cChat):
            chat_line = chat[i]
            if chat_line.startswith(">> "):
                clr = CLR_CHAT_RESP
            else:
                clr = CLR_CHAT_QUERY
            scr.addstr(y, 0, stripNonAscii(chat_line), clr)
            y += 1
    
    # Command line at the bottom
    l = line
    if len(line) > 0 and line[0] == ":":
        scr.addstr(curses.LINES-2, 0, "Command ('help' for options):", CLR_CMDLINE)
        scr.addstr(curses.LINES-1, 0, ":", CLR_CMDLINE)
        l = line[1:]
    else:
        scr.addstr(curses.LINES-2, 0, "Input (Ctrl+C to quit):", CLR_CMDLINE)
        scr.addstr(curses.LINES-1, 0, ">", CLR_CMDLINE)
    scr.addstr(curses.LINES-1, 2, l, CLR_INPUT)
    scr.refresh()
    

##############################################################################
# 

def handle_cmd(cmd):
    if "show" in cmd and "log" in cmd:
        pass
    elif "errors" in cmd:
        # Look in all logs for error messages, print here
        pass


def main(stdscr):
    global scr
    global ws
    global line
    
    scr = stdscr
    init_screen()
    
    ws = WebsocketClient()
   
    ws.on('speak', handle_speak)
    event_thread = Thread(target=connect)
    event_thread.setDaemon(True)
    event_thread.start()
    
    history = []
    hist_idx = -1  # index, from the bottom
    try:
        input = ""
        while True:
            draw_screen()
            # TODO: Change this mechanism
            # Sleep for a while so all the output that results
            # from the previous command finishes before we print.
            # time.sleep(1.5)

            # print("Input (Ctrl+C to quit):")
            c = scr.getch()
            if c == curses.KEY_ENTER or c == 10 or c == 13:
                if line == "":
                    continue
                    
                if line[:1] == ":":
                    handle_cmd(line[1:])
                else:
                    history.append(line)
                    chat.append(line)
                    ws.emit(
                        Message("recognizer_loop:utterance",
                                {'utterances': [line.strip()]}))
                hist_idx = -1
                line = ""               
            elif c == curses.KEY_UP:
                hist_idx = clamp(hist_idx+1, -1, len(history)-1)
                if hist_idx >= 0:
                    line = history[len(history)-hist_idx-1]
                else:
                    line = ""
            elif c == curses.KEY_DOWN:
                hist_idx = clamp(hist_idx-1, -1, len(history)-1)
                if hist_idx >= 0:
                    line = history[len(history)-hist_idx-1]
                else:
                    line = ""
            elif curses.ascii.isascii(c):
                line += chr(c)
            elif c == curses.KEY_BACKSPACE:
                line = line[:-1]
            else:
                line += str(c)
                pass
            # if line.startswith("*"):
            #     handle_cmd(line.strip("*"))
            # else:
            
    except KeyboardInterrupt, e:
        # User hit Ctrl+C to quit
        pass
    except KeyboardInterrupt, e:
        logger.exception(e)
        event_thread.exit()
        sys.exit()

startLogMonitor("scripts/logs/mycroft-skills.log")
startLogMonitor("scripts/logs/mycroft-voice.log")

if __name__ == "__main__":
   curses.wrapper(main)
 
