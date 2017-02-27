# Copyright 2017 Mycroft AI, Inc.
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
from cStringIO import StringIO

# NOTE: If this script has errors, the following two lines might need to
# be commented out for them to be displayed (depending on the type of
# error).  But normally we want this to prevent extra messages from the
# messagebus setup from appearing during startup.
sys.stdout = StringIO()  # capture any output
sys.stderr = StringIO()  # capture any output

# All of the nopep8 comments below are to avoid E402 errors
import os                                                   # nopep8
import os.path                                              # nopep8
import time                                                 # nopep8
import subprocess                                           # nopep8
import curses                                               # nopep8
import curses.ascii                                         # nopep8
from threading import Thread, Lock                          # nopep8
from mycroft.messagebus.client.ws import WebsocketClient    # nopep8
from mycroft.messagebus.message import Message              # nopep8
from mycroft.tts import TTSFactory                          # nopep8
from mycroft.util.log import getLogger                      # nopep8

tts = None
ws = None
mutex = Lock()
logger = getLogger("CLIClient")

utterances = []
chat = []
line = "What time is it"
bSimple = '--simple' in sys.argv
bQuiet = '--quiet' in sys.argv
scr = None
log_line_offset = 0  # num lines back in logs to show

mergedLog = []
log_filters = ["enclosure.mouth.viseme"]


##############################################################################
# Helper functions

def clamp(n, smallest, largest):
    return max(smallest, min(n, largest))


def stripNonAscii(text):
    return ''.join([i if ord(i) < 128 else ' ' for i in text])


##############################################################################
# Log file monitoring

class LogMonitorThread(Thread):
    def __init__(self, filename, logid):
        Thread.__init__(self)
        self.filename = filename
        self.st_results = os.stat(filename)
        self.logid = logid

    def run(self):
        global mergedLog

        while True:
            try:
                st_results = os.stat(self.filename)
                if not st_results.st_mtime == self.st_results.st_mtime:
                    self.read_file_from(self.st_results.st_size)
                    self.st_results = st_results
                    draw_screen()
            finally:
                time.sleep(0.1)

    def read_file_from(self, bytefrom):
        with open(self.filename, 'rb') as fh:
            fh.seek(bytefrom)
            while True:
                line = fh.readline()
                if line == "":
                    break

                # Allow user to filter log output
                ignore = False
                for filtered_text in log_filters:
                    if filtered_text in line:
                        ignore = True
                        break

                if not ignore:
                    if bSimple:
                        print line.strip()
                    else:
                        mergedLog.append(self.logid+line.strip())


def startLogMonitor(filename, logid):
    if os.path.isfile(filename):
        thread = LogMonitorThread(filename, logid)
        thread.setDaemon(True)  # this thread won't prevent prog from exiting
        thread.start()


##############################################################################
# Capturing output from Mycroft

def handle_speak(event):
    global chat
    global tts
    mutex.acquire()
    if not bQuiet:
        ws.emit(Message("recognizer_loop:audio_output_start"))
    try:
        utterance = event.data.get('utterance')
        if bSimple:
            print(">> " + utterance)
        else:
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
    global CLR_HEADING
    global CLR_CHAT_RESP
    global CLR_CHAT_QUERY
    global CLR_CMDLINE
    global CLR_INPUT
    global CLR_LOG1
    global CLR_LOG2
    global CLR_LOG_DEBUG

    if curses.has_colors():
        bg = curses.COLOR_WHITE
        for i in range(0, curses.COLORS):
            curses.init_pair(i + 1, i, bg)
            bg = curses.COLOR_BLACK

        # Colors:
        # 1 = black on white    9 = dk gray
        # 2 = dk red           10 = red
        # 3 = dk green         11 = green
        # 4 = dk yellow        12 = yellow
        # 5 = dk blue          13 = blue
        # 6 = dk purple        14 = purple
        # 7 = dk cyan          15 = cyan
        # 8 = lt gray          16 = white
        CLR_HEADING = curses.color_pair(16)
        CLR_CHAT_RESP = curses.color_pair(7)
        CLR_CHAT_QUERY = curses.color_pair(8)
        CLR_CMDLINE = curses.color_pair(15)
        CLR_INPUT = curses.color_pair(16)
        CLR_LOG1 = curses.color_pair(8)
        CLR_LOG2 = curses.color_pair(6)
        CLR_LOG_DEBUG = curses.color_pair(4)


def page_log(page_up):
    global log_line_offset
    if page_up:
        log_line_offset += 10
    else:
        log_line_offset -= 10
    if log_line_offset > len(mergedLog):
        log_line_offset = len(mergedLog)-10
    if log_line_offset < 0:
        log_line_offset = 0
    draw_screen()


def draw_screen():
    global scr
    global log_line_offset
    if not scr:
        return

    scr.clear()

    # Display log output at the top
    cLogs = len(mergedLog)
    cLogLinesToShow = curses.LINES-13
    start = clamp(cLogs - cLogLinesToShow, 0, cLogs - 1) - log_line_offset
    end = cLogs - log_line_offset
    if start < 0:
        end -= start
        start = 0
    if end > cLogs:
        end = cLogs

    # adjust the line offset (prevents paging up too far)
    log_line_offset = cLogs - end

    scr.addstr(0, 0, "Log Output:" + " " * (curses.COLS-31) + str(start) +
               "-" + str(end) + " of " + str(cLogs), CLR_HEADING)
    scr.addstr(1, 0,  "=" * (curses.COLS-1), CLR_HEADING)
    y = 2
    for i in range(start, end):
        log = mergedLog[i]
        logid = log[0]
        if len(log) > 25 and log[5] == '-' and log[8] == '-':
            log = log[27:]  # skip logid & date/time at the front of log line
        else:
            log = log[1:]   # just skip the logid

        # Categorize log line
        if "Skills - DEBUG - " in log:
            log = log.replace("Skills - DEBUG - ", "")
            clr = CLR_LOG_DEBUG
        else:
            if logid == "1":
                clr = CLR_LOG1
            else:
                clr = CLR_LOG2

        # limit line to screen width (show tail end)
        log = ("..."+log[-(curses.COLS-3):]) if len(log) > curses.COLS else log
        scr.addstr(y, 0, log, clr)
        y += 1

    # Log legend in the lower-right
    scr.addstr(curses.LINES-10, curses.COLS/2 + 2, "Log Output Legend",
               CLR_HEADING)
    scr.addstr(curses.LINES-9, curses.COLS/2 + 2, "=" * (curses.COLS/2 - 4),
               CLR_HEADING)
    scr.addstr(curses.LINES-8, curses.COLS/2 + 2,
               "mycroft-skills.log, system debug",
               CLR_LOG_DEBUG)
    scr.addstr(curses.LINES-7, curses.COLS/2 + 2,
               "mycroft-skills.log, other",
               CLR_LOG1)
    scr.addstr(curses.LINES-6, curses.COLS/2 + 2, "mycroft-voice.log",
               CLR_LOG2)

    # History log in the middle
    scr.addstr(curses.LINES-10, 0, "History", CLR_HEADING)
    scr.addstr(curses.LINES-9, 0,  "=" * (curses.COLS/2), CLR_HEADING)

    cChat = len(chat)
    if cChat:
        y = curses.LINES-8
        for i in range(cChat-clamp(cChat, 1, 5), cChat):
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
        scr.addstr(curses.LINES-2, 0, "Command ('help' for options):",
                   CLR_CMDLINE)
        scr.addstr(curses.LINES-1, 0, ":", CLR_CMDLINE)
        l = line[1:]
    else:
        scr.addstr(curses.LINES-2, 0,
                   "Input (':' for command mode, Ctrl+C to quit):",
                   CLR_CMDLINE)
        scr.addstr(curses.LINES-1, 0, ">", CLR_CMDLINE)
    scr.addstr(curses.LINES-1, 2, l, CLR_INPUT)
    scr.refresh()


def show_help():
    global scr
    if not scr:
        return

    scr.clear()
    scr.addstr(0, 0,  center(25) + "Mycroft Command Line Help",
               CLR_CMDLINE)
    scr.addstr(1, 0,  "=" * (curses.COLS-1),
               CLR_CMDLINE)
    scr.addstr(2, 0,  "Up / Down         scroll thru query history")
    scr.addstr(3, 0,  "Ctrl+PgUp / PgDn  scroll thru log history")

    scr.addstr(10, 0,  "Commands (type ':' to enter command mode)",
               CLR_CMDLINE)
    scr.addstr(11, 0,  "=" * (curses.COLS-1),
               CLR_CMDLINE)
    scr.addstr(12, 0,  ":help             this screen")
    scr.addstr(13, 0,  ":quit or :exit    exit the program")

    scr.addstr(curses.LINES-1, 0,  center(23) + "Press any key to return",
               CLR_HEADING)

    scr.refresh()
    c = scr.getch()


def center(str_len):
    # generate number of characters needed to center a string
    # of the given length
    return " " * ((curses.COLS - str_len) / 2)


##############################################################################
# Main UI

def handle_cmd(cmd):
    if "show" in cmd and "log" in cmd:
        pass
    elif "help" in cmd:
        show_help()
    elif "exit" in cmd or "quit" in cmd:
        return 1
    # TODO: More commands
    # elif "find" in cmd:
    #    ... search logs for given string
    return 0  # do nothing upon return


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

            c = scr.getch()
            if c == curses.KEY_ENTER or c == 10 or c == 13:
                if line == "":
                    continue

                if line[:1] == ":":
                    # Lines typed like ":help" are 'commands'
                    if handle_cmd(line[1:]) == 1:
                        break
                else:
                    # Treat this as an utterance
                    history.append(line)
                    chat.append(line)
                    ws.emit(Message("recognizer_loop:utterance",
                                    {'utterances': [line.strip()],
                                     'lang': 'en-us'}))
                hist_idx = -1
                line = ""
            elif c == curses.KEY_UP:
                # Move up the history stack
                hist_idx = clamp(hist_idx+1, -1, len(history)-1)
                if hist_idx >= 0:
                    line = history[len(history)-hist_idx-1]
                else:
                    line = ""
            elif c == curses.KEY_DOWN:
                # Move down the history stack
                hist_idx = clamp(hist_idx-1, -1, len(history)-1)
                if hist_idx >= 0:
                    line = history[len(history)-hist_idx-1]
                else:
                    line = ""
            elif curses.ascii.isascii(c):
                # Accept typed character
                line += chr(c)
            elif c == curses.KEY_BACKSPACE:
                line = line[:-1]
            elif c == 555:  # Ctrl+PgUp
                page_log(True)
                draw_screen()
            elif c == 550:  # Ctrl+PgUp
                page_log(False)
            elif c == curses.KEY_RESIZE:
                y, x = scr.getmaxyx()
                curses.resizeterm(y, x)

                # resizeterm() causes another curses.KEY_RESIZE, so
                # we need to capture that to prevent a loop of resizes
                c = scr.getch()

            # DEBUG: Uncomment the following code to see what key codes
            #        are generated when an unknown key is pressed.
            # else:
            #    line += str(c)

    except KeyboardInterrupt, e:
        # User hit Ctrl+C to quit
        pass
    except KeyboardInterrupt, e:
        logger.exception(e)
    finally:
        print "quitting"
        pass


def simple_cli():
    global ws
    ws = WebsocketClient()
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

# Find the correct log path relative to this script
scriptPath = os.path.dirname(os.path.realpath(__file__))
localLogPath = os.path.realpath(scriptPath+"/../../../scripts/logs")

# Monitor relative logs (for Github installs)
startLogMonitor(localLogPath + "/mycroft-skills.log", "1")
startLogMonitor(localLogPath + "/mycroft-voice.log", "2")

# Also monitor system logs (for package installs)
startLogMonitor("/var/log/mycroft-skills.log", "1")
startLogMonitor("/var/log/mycroft-voice.log", "2")

if __name__ == "__main__":
    if bSimple:
        sys.stdout = sys.__stdout__
        sys.stderr = sys.__stderr__
        simple_cli()
    else:
        curses.wrapper(main)
