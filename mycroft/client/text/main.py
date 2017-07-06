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
import textwrap                                             # nopep8
import json                                                 # nopep8
from threading import Thread, Lock                          # nopep8
from mycroft.messagebus.client.ws import WebsocketClient    # nopep8
from mycroft.messagebus.message import Message              # nopep8
from mycroft.tts import TTSFactory                          # nopep8
from mycroft.util import get_ipc_directory                  # nopep8
from mycroft.util.log import getLogger                      # nopep8
from mycroft.configuration import ConfigurationManager      # nopep8

tts = None
ws = None
mutex = Lock()
logger = getLogger("CLIClient")

utterances = []
chat = []   # chat history, oldest at the lowest index
line = "What time is it"
bSimple = '--simple' in sys.argv
bQuiet = '--quiet' in sys.argv
scr = None
log_line_offset = 0  # num lines back in logs to show
log_line_lr_scroll = 0  # amount to scroll left/right for long lines
longest_visible_line = 0  # for HOME key

mergedLog = []
filteredLog = []
default_log_filters = ["enclosure.mouth.viseme"]
log_filters = list(default_log_filters)
log_files = []

# Values used to display the audio meter
show_meter = True
meter_peak = 20
meter_cur = -1
meter_thresh = -1

screen_mode = 0   # 0 = main, 1 = help, others in future?
last_redraw = 0   # time when last full-redraw happened

##############################################################################
# Helper functions


def clamp(n, smallest, largest):
    """ Force n to be between smallest and largest, inclusive """
    return max(smallest, min(n, largest))


def stripNonAscii(text):
    """ Remove junk characters that might be in the file """
    return ''.join([i if ord(i) < 128 else ' ' for i in text])


##############################################################################
# Settings

config_file = os.path.join(os.path.expanduser("~"), ".mycroft_cli.conf")


def load_settings():
    global log_filters

    try:
        with open(config_file, 'r') as f:
            config = json.load(f)
        if "filters" in config:
            log_filters = config["filters"]
    except:
        pass


def save_settings():
    config["filters"] = log_filters
    with open(config_file, 'w') as f:
        json.dump(config, f)


##############################################################################
# Log file monitoring

class LogMonitorThread(Thread):
    def __init__(self, filename, logid):
        global log_files
        Thread.__init__(self)
        self.filename = filename
        self.st_results = os.stat(filename)
        self.logid = str(logid)
        log_files.append(filename)

    def run(self):
        while True:
            try:
                st_results = os.stat(self.filename)

                # Check if file has been modified since last read
                if not st_results.st_mtime == self.st_results.st_mtime:
                    self.read_file_from(self.st_results.st_size)
                    self.st_results = st_results
                    draw_screen()
            finally:
                time.sleep(0.1)

    def read_file_from(self, bytefrom):
        global meter_cur
        global meter_thresh
        global filteredLog
        global mergedLog

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

                if ignore:
                    mergedLog.append(self.logid+line.strip())
                else:
                    if bSimple:
                        print line.strip()
                    else:
                        filteredLog.append(self.logid+line.strip())
                        mergedLog.append(self.logid+line.strip())


def start_log_monitor(filename):
    if os.path.isfile(filename):
        thread = LogMonitorThread(filename, len(log_files))
        thread.setDaemon(True)  # this thread won't prevent prog from exiting
        thread.start()


class MicMonitorThread(Thread):
    def __init__(self, filename):
        Thread.__init__(self)
        self.filename = filename
        self.st_results = os.stat(filename)

    def run(self):
        while True:
            try:
                st_results = os.stat(self.filename)

                if (not st_results.st_ctime == self.st_results.st_ctime or
                        not st_results.st_mtime == self.st_results.st_mtime):
                    self.read_file_from(0)
                    self.st_results = st_results
                    draw_screen()
            finally:
                time.sleep(0.1)

    def read_file_from(self, bytefrom):
        global meter_cur
        global meter_thresh

        with open(self.filename, 'rb') as fh:
            fh.seek(bytefrom)
            while True:
                line = fh.readline()
                if line == "":
                    break

                # Just adjust meter settings
                # Ex:Energy:  cur=4 thresh=1.5
                parts = line.split("=")
                meter_thresh = float(parts[len(parts)-1])
                meter_cur = float(parts[len(parts)-2].split(" ")[0])


def start_mic_monitor(filename):
    if os.path.isfile(filename):
        thread = MicMonitorThread(filename)
        thread.setDaemon(True)  # this thread won't prevent prog from exiting
        thread.start()


def add_log_message(message):
    """ Show a message for the user (mixed in the logs) """
    global filteredLog
    global mergedLog

    message = "@"+message       # the first byte is a code
    filteredLog.append(message)
    mergedLog.append(message)
    scr.erase()
    scr.refresh()


def rebuild_filtered_log():
    global filteredLog
    global mergedLog

    filteredLog = []
    for line in mergedLog:
        # Apply filters
        ignore = False
        for filtered_text in log_filters:
            if filtered_text in line:
                ignore = True
                break

        if not ignore:
            filteredLog.append(line)


##############################################################################
# Capturing output from Mycroft

def handle_speak(event):
    global chat
    utterance = event.data.get('utterance')
    if bSimple:
        print(">> " + utterance)
    else:
        chat.append(">> " + utterance)
    draw_screen()
    if not bQuiet:
        global tts

        mutex.acquire()
        if not tts:
            tts = TTSFactory.create()
            tts.init(ws)
        try:
            tts.execute(utterance)
        finally:
            mutex.release()


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
    global CLR_LOG_CMDMESSAGE
    global CLR_METER_CUR
    global CLR_METER

    if curses.has_colors():
        curses.init_pair(1, curses.COLOR_WHITE, curses.COLOR_BLACK)
        bg = curses.COLOR_BLACK
        for i in range(1, curses.COLORS):
            curses.init_pair(i + 1, i, bg)

        # Colors (on black backgound):
        # 1 = white         5 = dk blue
        # 2 = dk red        6 = dk purple
        # 3 = dk green      7 = dk cyan
        # 4 = dk yellow     8 = lt gray
        CLR_HEADING = curses.color_pair(1)
        CLR_CHAT_RESP = curses.color_pair(4)
        CLR_CHAT_QUERY = curses.color_pair(7)
        CLR_CMDLINE = curses.color_pair(7)
        CLR_INPUT = curses.color_pair(7)
        CLR_LOG1 = curses.color_pair(3)
        CLR_LOG2 = curses.color_pair(6)
        CLR_LOG_DEBUG = curses.color_pair(4)
        CLR_LOG_CMDMESSAGE = curses.color_pair(2)
        CLR_METER_CUR = curses.color_pair(2)
        CLR_METER = curses.color_pair(4)


def page_log(page_up):
    global log_line_offset
    if page_up:
        log_line_offset += 10
    else:
        log_line_offset -= 10
    if log_line_offset > len(filteredLog):
        log_line_offset = len(filteredLog)-10
    if log_line_offset < 0:
        log_line_offset = 0
    draw_screen()


def draw_meter():
    if not show_meter or meter_cur == -1:
        return

    # The meter will look something like this:
    #
    # 8.4   *
    #       *
    #      -*- 2.4
    #       *
    #       *
    #       *
    # Where the left side is the current level and the right side is
    # the threshold level for 'silence'.
    global scr
    global meter_peak

    if meter_cur > meter_peak:
        meter_peak = meter_cur+1

    height = curses.LINES/3
    scale = meter_peak
    if meter_peak > meter_thresh*3:
        scale = meter_thresh*3
    h_cur = clamp(int((float(meter_cur) / scale) * height), 0, height-1)
    h_thresh = clamp(int((float(meter_thresh) / scale) * height), 0, height-1)
    clr = curses.color_pair(4)  # dark yellow

    str_level = "{0:3} ".format(int(meter_cur))   # e.g. '  4'
    str_thresh = "{0:4.2f}".format(meter_thresh)  # e.g. '3.24'
    meter_width = len(str_level) + len(str_thresh) + 4
    for i in range(0, height):
        meter = ""
        if i == h_cur:
            # current energy level
            meter = str_level
        else:
            meter = " " * len(str_level)

        if i == h_thresh:
            # add threshold indicator
            meter += "--- "
        else:
            meter += "    "

        if i == h_thresh:
            # 'silence' threshold energy level
            meter += str_thresh

        # draw the line
        meter += " " * (meter_width - len(meter))
        scr.addstr(curses.LINES-1-i, curses.COLS-len(meter)-1, meter, clr)

        # draw an asterisk if the audio energy is at this level
        if i <= h_cur:
            if meter_cur > meter_thresh:
                clr_bar = curses.color_pair(3)   # dark green for loud
            else:
                clr_bar = curses.color_pair(5)   # dark blue for 'silent'
            scr.addstr(curses.LINES-1-i, curses.COLS-len(str_thresh)-4, "*",
                       clr_bar)


def draw_screen():
    global scr
    global log_line_offset
    global longest_visible_line
    global last_redraw

    if not scr:
        return

    if not screen_mode == 0:
        return

    if time.time() - last_redraw > 5:   # every 5 seconds
        scr.clear()
        last_redraw = time.time()
    else:
        scr.erase()

    # Display log output at the top
    cLogs = len(filteredLog)
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
    len_line = 0
    for i in range(start, end):
        log = filteredLog[i]
        logid = log[0]
        if len(log) > 25 and log[5] == '-' and log[8] == '-':
            log = log[27:]  # skip logid & date/time at the front of log line
        else:
            log = log[1:]   # just skip the logid

        # Categorize log line
        if " - DEBUG - " in log:
            log = log.replace("Skills ", "")
            clr = CLR_LOG_DEBUG
        else:
            if logid == "1":
                clr = CLR_LOG1
            elif logid == "@":
                clr = CLR_LOG_CMDMESSAGE
            else:
                clr = CLR_LOG2

        # limit output line to screen width
        len_line = len(log)
        if len(log) > curses.COLS:
            start = len_line - (curses.COLS - 4) - log_line_lr_scroll
            if start < 0:
                start = 0
            end = start + (curses.COLS - 4)
            if start == 0:
                log = log[start:end] + "~~~~"   # start....
            elif end >= len_line-1:
                log = "~~~~" + log[start:end]   # ....end
            else:
                log = "~~" + log[start:end] + "~~"  # ..middle..
        if len_line > longest_visible_line:
            longest_visible_line = len_line
        scr.addstr(y, 0, log, clr)
        y += 1

    # Log legend in the lower-right
    scr.addstr(curses.LINES-10, curses.COLS/2 + 2,
               make_titlebar("Log Output Legend", curses.COLS/2 - 2),
               CLR_HEADING)
    scr.addstr(curses.LINES-9, curses.COLS/2 + 2,
               "DEBUG output",
               CLR_LOG_DEBUG)
    scr.addstr(curses.LINES-8, curses.COLS/2 + 2,
               os.path.basename(log_files[0])+", other",
               CLR_LOG1)
    if len(log_files) > 1:
        scr.addstr(curses.LINES-7, curses.COLS/2 + 2,
                   os.path.basename(log_files[1]), CLR_LOG2)

    # History log in the middle
    chat_width = curses.COLS/2 - 2
    chat_height = 7
    chat_out = []
    scr.addstr(curses.LINES-10, 0, make_titlebar("History", chat_width),
               CLR_HEADING)

    # Build a nicely wrapped version of the chat log
    idx_chat = len(chat)-1
    while len(chat_out) < chat_height and idx_chat >= 0:
        if chat[idx_chat][0] == '>':
            wrapper = textwrap.TextWrapper(initial_indent="",
                                           subsequent_indent="   ",
                                           width=chat_width)
        else:
            wrapper = textwrap.TextWrapper(width=chat_width)

        chatlines = wrapper.wrap(chat[idx_chat])
        for txt in reversed(chatlines):
            if len(chat_out) >= chat_height:
                break
            chat_out.insert(0, txt)

        idx_chat -= 1

    # Output the chat
    y = curses.LINES-9
    for txt in chat_out:
        if txt.startswith(">> ") or txt.startswith("   "):
            clr = CLR_CHAT_RESP
        else:
            clr = CLR_CHAT_QUERY
        scr.addstr(y, 1, stripNonAscii(txt), clr)
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
                   make_titlebar("Input (':' for command, Ctrl+C to quit)",
                                 curses.COLS-1),
                   CLR_HEADING)
        scr.addstr(curses.LINES-1, 0, ">", CLR_HEADING)

    draw_meter()
    scr.addstr(curses.LINES-1, 2, l, CLR_INPUT)
    scr.refresh()


def make_titlebar(title, bar_length):
    return title + " " + ("=" * (bar_length - 1 - len(title)))


def show_help():
    global scr
    global screen_mode

    if not scr:
        return

    screen_mode = 1  # showing help (prevents overwrite by log updates)
    scr.erase()
    scr.addstr(0, 0,  center(25) + "Mycroft Command Line Help",
               CLR_CMDLINE)
    scr.addstr(1, 0,  "=" * (curses.COLS-1),
               CLR_CMDLINE)
    scr.addstr(2, 0,  "Up / Down         scroll thru query history")
    scr.addstr(3, 0,  "PgUp / PgDn       scroll thru log history")
    scr.addstr(4, 0,  "Left / Right      scroll long log lines left/right")
    scr.addstr(5, 0,  "Home              scroll to start of long log lines")
    scr.addstr(6, 0,  "End               scroll to end of long log lines")

    scr.addstr(10, 0,  "Commands (type ':' to enter command mode)",
               CLR_CMDLINE)
    scr.addstr(11, 0,  "=" * (curses.COLS-1),
               CLR_CMDLINE)
    scr.addstr(12, 0,  ":help                   this screen")
    scr.addstr(13, 0,  ":quit or :exit          exit the program")
    scr.addstr(14, 0,  ":meter (show|hide)      display of microphone level")
    scr.addstr(15, 0,  ":filter [remove] 'str'  adds or removes a log filter")
    scr.addstr(16, 0,  ":filter (clear|reset)   reset filters")
    scr.addstr(17, 0,  ":filter (show|list)     display current filters")

    scr.addstr(curses.LINES-1, 0,  center(23) + "Press any key to return",
               CLR_HEADING)

    scr.refresh()
    c = scr.getch()  # blocks

    screen_mode = 0  # back to main screen
    draw_screen()


def center(str_len):
    # generate number of characters needed to center a string
    # of the given length
    return " " * ((curses.COLS - str_len) / 2)


##############################################################################
# Main UI lopo

def handle_cmd(cmd):
    global show_meter
    global log_filters
    global mergedLog

    if "show" in cmd and "log" in cmd:
        pass
    elif "help" in cmd:
        show_help()
    elif "exit" in cmd or "quit" in cmd:
        return 1
    elif "meter" in cmd:
        # microphone level meter
        if "hide" in cmd or "off" in cmd:
            show_meter = False
        elif "show" in cmd or "on" in cmd:
            show_meter = True
    elif "filter" in cmd:
        if "show" in cmd or "list" in cmd:
            # display active filters
            add_log_message("Filters: "+str(log_filters))
            return

        if "reset" in cmd or "clear" in cmd:
            log_filters = list(default_log_filters)
        else:
            # extract last word(s)
            cmd = cmd.strip()
            last_char = cmd[-1]
            if last_char == '"' or last_char == "'":
                parts = cmd.split(last_char)
                word = parts[-2]
            else:
                parts = cmd.split(" ")
                word = parts[-1]

            if "remove" in cmd and word in log_filters:
                log_filters.remove(word)
            else:
                log_filters.append(word)

        rebuild_filtered_log()
        add_log_message("Filters: "+str(log_filters))

    # TODO: More commands
    # elif "find" in cmd:
    #    ... search logs for given string
    return 0  # do nothing upon return


def main(stdscr):
    global scr
    global ws
    global line
    global log_line_lr_scroll
    global longest_visible_line

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

            # Convert VT100 ESC codes generated by some terminals
            if c == 27:
                c1 = scr.getch()
                c2 = scr.getch()
                if c1 == 79 and c2 == 120:
                    c = curses.KEY_UP
                elif c1 == 79 and c2 == 116:
                    c = curses.KEY_LEFT
                elif c1 == 79 and c2 == 114:
                    c = curses.KEY_DOWN
                elif c1 == 79 and c2 == 118:
                    c = curses.KEY_RIGHT
                elif c1 == 79 and c2 == 121:
                    c = curses.KEY_NPAGE  # aka PgUp
                elif c1 == 79 and c2 == 115:
                    c = curses.KEY_PPAGE  # aka PgDn
                elif c1 == 79 and c2 == 119:
                    c = curses.KEY_HOME
                elif c1 == 79 and c2 == 113:
                    c = curses.KEY_END
                else:
                    c = c2

            if c == curses.KEY_ENTER or c == 10 or c == 13:
                # ENTER sends the typed line to be processed by Mycroft
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
            elif c == curses.KEY_LEFT:
                # scroll long log lines left
                log_line_lr_scroll += curses.COLS/4
            elif c == curses.KEY_RIGHT:
                # scroll long log lines right
                log_line_lr_scroll -= curses.COLS/4
                if log_line_lr_scroll < 0:
                    log_line_lr_scroll = 0
            elif c == curses.KEY_HOME:
                # HOME scrolls log lines all the way to the start
                log_line_lr_scroll = longest_visible_line
            elif c == curses.KEY_END:
                # END scrolls log lines all the way to the end
                log_line_lr_scroll = 0
            elif c == curses.KEY_NPAGE or c == 555:  # Ctrl+PgUp
                # PgUp to go up a page in the logs
                page_log(True)
                draw_screen()
            elif c == curses.KEY_PPAGE or c == 550:  # Ctrl+PgUp
                # PgDn to go down a page in the logs
                page_log(False)
            elif c == curses.KEY_RESIZE:
                # Generated by Curses when window/screen has been resized
                y, x = scr.getmaxyx()
                curses.resizeterm(y, x)

                # resizeterm() causes another curses.KEY_RESIZE, so
                # we need to capture that to prevent a loop of resizes
                c = scr.getch()
            elif c == curses.KEY_BACKSPACE or c == 127:
                # Backspace to erase a character in the utterance
                line = line[:-1]
            elif curses.ascii.isascii(c):
                # Accept typed character in the utterance
                line += chr(c)

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
        scr.erase()
        scr.refresh()
        scr = None
        pass


def simple_cli():
    global ws
    ws = WebsocketClient()
    event_thread = Thread(target=connect)
    event_thread.setDaemon(True)
    event_thread.start()
    try:
        while True:
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
start_log_monitor(localLogPath + "/mycroft-skills.log")
start_log_monitor(localLogPath + "/mycroft-voice.log")

# Also monitor system logs (for package installs)
start_log_monitor("/var/log/mycroft-skills.log")
start_log_monitor("/var/log/mycroft-speech-client.log")

# Monitor IPC file containing microphone level info
start_mic_monitor(os.path.join(get_ipc_directory(), "mic_level"))

if __name__ == "__main__":
    if bSimple:
        sys.stdout = sys.__stdout__
        sys.stderr = sys.__stderr__
        simple_cli()
    else:
        load_settings()
        curses.wrapper(main)
        curses.endwin()
        save_settings()
