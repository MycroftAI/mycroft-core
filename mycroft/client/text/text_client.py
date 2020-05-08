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
import sys
import io
from math import ceil
from xdg import BaseDirectory

from .gui_server import start_qml_gui

from mycroft.tts import TTS

import os
import os.path
import time
import curses
import textwrap
import json
import mycroft.version
from threading import Thread, Lock
from mycroft.messagebus.client import MessageBusClient
from mycroft.messagebus.message import Message
from mycroft.util.log import LOG
from mycroft.configuration import Configuration

import locale
# Curses uses LC_ALL to determine how to display chars set it to system
# default
locale.setlocale(locale.LC_ALL, "")  # Set LC_ALL to user default
preferred_encoding = locale.getpreferredencoding()

bSimple = False
bus = None  # Mycroft messagebus connection
config = {}  # Will be populated by the Mycroft configuration
event_thread = None
history = []
chat = []   # chat history, oldest at the lowest index
line = ""
scr = None
log_line_offset = 0  # num lines back in logs to show
log_line_lr_scroll = 0  # amount to scroll left/right for long lines
longest_visible_line = 0  # for HOME key
auto_scroll = True

# for debugging odd terminals
last_key = ""
show_last_key = False
show_gui = None  # None = not initialized, else True/False
gui_text = []

log_lock = Lock()
max_log_lines = 5000
mergedLog = []
filteredLog = []
default_log_filters = ["mouth.viseme", "mouth.display", "mouth.icon"]
log_filters = list(default_log_filters)
log_files = []
find_str = None
cy_chat_area = 7  # default chat history height (in lines)
size_log_area = 0  # max number of visible log lines, calculated during draw


# Values used to display the audio meter
show_meter = True
meter_peak = 20
meter_cur = -1
meter_thresh = -1

SCR_MAIN = 0
SCR_HELP = 1
SCR_SKILLS = 2
screen_mode = SCR_MAIN

subscreen = 0     # for help pages, etc.
REDRAW_FREQUENCY = 10    # seconds between full redraws
last_redraw = time.time() - (REDRAW_FREQUENCY - 1)  # seed for 1s redraw
screen_lock = Lock()
is_screen_dirty = True

# Curses color codes (reassigned at runtime)
CLR_HEADING = 0
CLR_FIND = 0
CLR_CHAT_RESP = 0
CLR_CHAT_QUERY = 0
CLR_CMDLINE = 0
CLR_INPUT = 0
CLR_LOG1 = 0
CLR_LOG2 = 0
CLR_LOG_DEBUG = 0
CLR_LOG_ERROR = 0
CLR_LOG_CMDMESSAGE = 0
CLR_METER_CUR = 0
CLR_METER = 0

# Allow Ctrl+C catching...
ctrl_c_was_pressed = False


def ctrl_c_handler(signum, frame):
    global ctrl_c_was_pressed
    ctrl_c_was_pressed = True


def ctrl_c_pressed():
    global ctrl_c_was_pressed
    if ctrl_c_was_pressed:
        ctrl_c_was_pressed = False
        return True
    else:
        return False


##############################################################################
# Helper functions

def clamp(n, smallest, largest):
    """ Force n to be between smallest and largest, inclusive """
    return max(smallest, min(n, largest))


def handleNonAscii(text):
    """
        If default locale supports UTF-8 reencode the string otherwise
        remove the offending characters.
    """
    if preferred_encoding == 'ASCII':
        return ''.join([i if ord(i) < 128 else ' ' for i in text])
    else:
        return text.encode(preferred_encoding)


##############################################################################
# Settings

filename = "mycroft_cli.conf"


def load_mycroft_config(bus):
    """ Load the mycroft config and connect it to updates over the messagebus.
    """
    Configuration.set_config_update_handlers(bus)
    return Configuration.get()


def connect_to_mycroft():
    """ Connect to the mycroft messagebus and load and register config
        on the bus.

        Sets the bus and config global variables
    """
    global bus
    global config
    bus = connect_to_messagebus()
    config = load_mycroft_config(bus)


def load_settings():
    global log_filters
    global cy_chat_area
    global show_last_key
    global max_log_lines
    global show_meter

    config_file = None

    # Old location
    path = os.path.join(os.path.expanduser("~"), ".mycroft_cli.conf")
    if os.path.isfile(path):
        LOG.warning(" ===============================================")
        LOG.warning(" ==             DEPRECATION WARNING           ==")
        LOG.warning(" ===============================================")
        LOG.warning(" You still have a config file at " +
                    path)
        LOG.warning(" Note that this location is deprecated and will" +
                    " not be used in the future")
        LOG.warning(" Please move it to " +
                    os.path.join(BaseDirectory.save_config_path('mycroft'),
                                 filename))
        config_file = path

    # Check XDG_CONFIG_DIR
    if config_file is None:
        for dir in BaseDirectory.load_config_paths('mycroft'):
            file = os.path.join(dir, filename)
            if os.path.isfile(file):
                config_file = file
                break

    # Check /etc/mycroft
    if config_file is None:
        config_file = os.path.join("/etc/mycroft", filename)

    try:
        with io.open(config_file, 'r') as f:
            config = json.load(f)
        if "filters" in config:
            # Disregard the filtering of DEBUG messages
            log_filters = [f for f in config["filters"] if f != "DEBUG"]
        if "cy_chat_area" in config:
            cy_chat_area = config["cy_chat_area"]
        if "show_last_key" in config:
            show_last_key = config["show_last_key"]
        if "max_log_lines" in config:
            max_log_lines = config["max_log_lines"]
        if "show_meter" in config:
            show_meter = config["show_meter"]
    except Exception as e:
        LOG.info("Ignoring failed load of settings file")


def save_settings():
    config = {}
    config["filters"] = log_filters
    config["cy_chat_area"] = cy_chat_area
    config["show_last_key"] = show_last_key
    config["max_log_lines"] = max_log_lines
    config["show_meter"] = show_meter

    config_file = os.path.join(
        BaseDirectory.save_config_path("mycroft"), filename)

    with io.open(config_file, 'w') as f:
        f.write(str(json.dumps(config, ensure_ascii=False)))


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

                    set_screen_dirty()
            except OSError:
                # ignore any file IO exceptions, just try again
                pass
            time.sleep(0.1)

    def read_file_from(self, bytefrom):
        global meter_cur
        global meter_thresh
        global filteredLog
        global mergedLog
        global log_line_offset
        global log_lock

        with io.open(self.filename) as fh:
            fh.seek(bytefrom)
            while True:
                line = fh.readline()
                if line == "":
                    break

                # Allow user to filter log output
                ignore = False
                if find_str:
                    if find_str not in line:
                        ignore = True
                else:
                    for filtered_text in log_filters:
                        if filtered_text in line:
                            ignore = True
                            break

                with log_lock:
                    if ignore:
                        mergedLog.append(self.logid + line.rstrip())
                    else:
                        if bSimple:
                            print(line.rstrip())
                        else:
                            filteredLog.append(self.logid + line.rstrip())
                            mergedLog.append(self.logid + line.rstrip())
                            if not auto_scroll:
                                log_line_offset += 1

        # Limit log to  max_log_lines
        if len(mergedLog) >= max_log_lines:
            with log_lock:
                cToDel = len(mergedLog) - max_log_lines
                if len(filteredLog) == len(mergedLog):
                    del filteredLog[:cToDel]
                del mergedLog[:cToDel]

            # release log_lock before calling to prevent deadlock
            if len(filteredLog) != len(mergedLog):
                rebuild_filtered_log()


def start_log_monitor(filename):
    if os.path.isfile(filename):
        thread = LogMonitorThread(filename, len(log_files))
        thread.setDaemon(True)  # this thread won't prevent prog from exiting
        thread.start()


class MicMonitorThread(Thread):
    def __init__(self, filename):
        Thread.__init__(self)
        self.filename = filename
        self.st_results = None

    def run(self):
        while True:
            try:
                st_results = os.stat(self.filename)

                if (not self.st_results or
                        not st_results.st_ctime == self.st_results.st_ctime or
                        not st_results.st_mtime == self.st_results.st_mtime):
                    self.read_mic_level()
                    self.st_results = st_results
                    set_screen_dirty()
            except Exception:
                # Ignore whatever failure happened and just try again later
                pass
            time.sleep(0.2)

    def read_mic_level(self):
        global meter_cur
        global meter_thresh

        with io.open(self.filename, 'r') as fh:
            line = fh.readline()
            # Just adjust meter settings
            # Ex:Energy:  cur=4 thresh=1.5 muted=0
            cur_text, thresh_text, _ = line.split(' ')[-3:]
            meter_thresh = float(thresh_text.split('=')[-1])
            meter_cur = float(cur_text.split('=')[-1])


class ScreenDrawThread(Thread):
    def __init__(self):
        Thread.__init__(self)

    def run(self):
        global scr
        global screen_lock
        global is_screen_dirty
        global log_lock

        while scr:
            try:
                if is_screen_dirty:
                    # Use a lock to prevent screen corruption when drawing
                    # from multiple threads
                    with screen_lock:
                        is_screen_dirty = False

                        if screen_mode == SCR_MAIN:
                            with log_lock:
                                do_draw_main(scr)
                        elif screen_mode == SCR_HELP:
                            do_draw_help(scr)

            finally:
                time.sleep(0.01)


def start_mic_monitor(filename):
    if os.path.isfile(filename):
        thread = MicMonitorThread(filename)
        thread.setDaemon(True)  # this thread won't prevent prog from exiting
        thread.start()


def add_log_message(message):
    """ Show a message for the user (mixed in the logs) """
    global filteredLog
    global mergedLog
    global log_line_offset
    global log_lock

    with log_lock:
        message = "@" + message       # the first byte is a code
        filteredLog.append(message)
        mergedLog.append(message)

        if log_line_offset != 0:
            log_line_offset = 0  # scroll so the user can see the message
    set_screen_dirty()


def clear_log():
    global filteredLog
    global mergedLog
    global log_line_offset
    global log_lock

    with log_lock:
        mergedLog = []
        filteredLog = []
        log_line_offset = 0


def rebuild_filtered_log():
    global filteredLog
    global mergedLog
    global log_lock

    with log_lock:
        filteredLog = []
        for line in mergedLog:
            # Apply filters
            ignore = False

            if find_str and find_str != "":
                # Searching log
                if find_str not in line:
                    ignore = True
            else:
                # Apply filters
                for filtered_text in log_filters:
                    if filtered_text and filtered_text in line:
                        ignore = True
                        break

            if not ignore:
                filteredLog.append(line)


##############################################################################
# Capturing output from Mycroft

def handle_speak(event):
    global chat
    utterance = event.data.get('utterance')
    utterance = TTS.remove_ssml(utterance)
    if bSimple:
        print(">> " + utterance)
    else:
        chat.append(">> " + utterance)
    set_screen_dirty()


def handle_utterance(event):
    global chat
    global history
    utterance = event.data.get('utterances')[0]
    history.append(utterance)
    chat.append(utterance)
    set_screen_dirty()


def connect(bus):
    """ Run the mycroft messagebus referenced by bus.

        Args:
            bus:    Mycroft messagebus instance
    """
    bus.run_forever()


##############################################################################
# Capturing the messagebus

def handle_message(msg):
    # TODO: Think this thru a little bit -- remove this logging within core?
    # add_log_message(msg)
    pass


##############################################################################
# "Graphic primitives"
def draw(x, y, msg, pad=None, pad_chr=None, clr=None):
    """Draw a text to the screen

    Args:
        x (int): X coordinate (col), 0-based from upper-left
        y (int): Y coordinate (row), 0-based from upper-left
        msg (str): string to render to screen
        pad (bool or int, optional): if int, pads/clips to given length, if
                                     True use right edge of the screen.
        pad_chr (char, optional): pad character, default is space
        clr (int, optional): curses color, Defaults to CLR_LOG1.
    """
    if y < 0 or y > curses.LINES or x < 0 or x > curses.COLS:
        return

    if x + len(msg) > curses.COLS:
        s = msg[:curses.COLS - x]
    else:
        s = msg
        if pad:
            ch = pad_chr or " "
            if pad is True:
                pad = curses.COLS  # pad to edge of screen
                s += ch * (pad - x - len(msg))
            else:
                # pad to given length (or screen width)
                if x + pad > curses.COLS:
                    pad = curses.COLS - x
                s += ch * (pad - len(msg))

    if not clr:
        clr = CLR_LOG1

    scr.addstr(y, x, s, clr)


##############################################################################
# Screen handling


def init_screen():
    global CLR_HEADING
    global CLR_FIND
    global CLR_CHAT_RESP
    global CLR_CHAT_QUERY
    global CLR_CMDLINE
    global CLR_INPUT
    global CLR_LOG1
    global CLR_LOG2
    global CLR_LOG_DEBUG
    global CLR_LOG_ERROR
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
        CLR_FIND = curses.color_pair(4)
        CLR_CMDLINE = curses.color_pair(7)
        CLR_INPUT = curses.color_pair(7)
        CLR_LOG1 = curses.color_pair(3)
        CLR_LOG2 = curses.color_pair(6)
        CLR_LOG_DEBUG = curses.color_pair(4)
        CLR_LOG_ERROR = curses.color_pair(2)
        CLR_LOG_CMDMESSAGE = curses.color_pair(2)
        CLR_METER_CUR = curses.color_pair(2)
        CLR_METER = curses.color_pair(4)


def scroll_log(up, num_lines=None):
    global log_line_offset

    # default to a half-page
    if not num_lines:
        num_lines = size_log_area // 2

    with log_lock:
        if up:
            log_line_offset -= num_lines
        else:
            log_line_offset += num_lines
        if log_line_offset > len(filteredLog):
            log_line_offset = len(filteredLog) - 10
        if log_line_offset < 0:
            log_line_offset = 0
    set_screen_dirty()


def _do_meter(height):
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
        meter_peak = meter_cur + 1

    scale = meter_peak
    if meter_peak > meter_thresh * 3:
        scale = meter_thresh * 3
    h_cur = clamp(int((float(meter_cur) / scale) * height), 0, height - 1)
    h_thresh = clamp(
        int((float(meter_thresh) / scale) * height), 0, height - 1)
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
        scr.addstr(curses.LINES - 1 - i, curses.COLS -
                   len(meter) - 1, meter, clr)

        # draw an asterisk if the audio energy is at this level
        if i <= h_cur:
            if meter_cur > meter_thresh:
                clr_bar = curses.color_pair(3)   # dark green for loud
            else:
                clr_bar = curses.color_pair(5)   # dark blue for 'silent'
            scr.addstr(curses.LINES - 1 - i, curses.COLS - len(str_thresh) - 4,
                       "*", clr_bar)


def _do_gui(gui_width):
    clr = curses.color_pair(2)  # dark red
    x = curses.COLS - gui_width
    y = 3
    draw(
        x,
        y,
        " " +
        make_titlebar(
            "= GUI",
            gui_width -
            1) +
        " ",
        clr=CLR_HEADING)
    cnt = len(gui_text) + 1
    if cnt > curses.LINES - 15:
        cnt = curses.LINES - 15
    for i in range(0, cnt):
        draw(x, y + 1 + i, " !", clr=CLR_HEADING)
        if i < len(gui_text):
            draw(x + 2, y + 1 + i, gui_text[i], pad=gui_width - 3)
        else:
            draw(x + 2, y + 1 + i, "*" * (gui_width - 3))
        draw(x + (gui_width - 1), y + 1 + i, "!", clr=CLR_HEADING)
    draw(x, y + cnt, " " + "-" * (gui_width - 2) + " ", clr=CLR_HEADING)


def set_screen_dirty():
    global is_screen_dirty
    global screen_lock

    with screen_lock:
        is_screen_dirty = True


def do_draw_main(scr):
    global log_line_offset
    global longest_visible_line
    global last_redraw
    global auto_scroll
    global size_log_area

    if time.time() - last_redraw > REDRAW_FREQUENCY:
        # Do a full-screen redraw periodically to clear and
        # noise from non-curses text that get output to the
        # screen (e.g. modules that do a 'print')
        scr.clear()
        last_redraw = time.time()
    else:
        scr.erase()

    # Display log output at the top
    cLogs = len(filteredLog) + 1  # +1 for the '--end--'
    size_log_area = curses.LINES - (cy_chat_area + 5)
    start = clamp(cLogs - size_log_area, 0, cLogs - 1) - log_line_offset
    end = cLogs - log_line_offset
    if start < 0:
        end -= start
        start = 0
    if end > cLogs:
        end = cLogs

    auto_scroll = (end == cLogs)

    # adjust the line offset (prevents paging up too far)
    log_line_offset = cLogs - end

    # Top header and line counts
    if find_str:
        scr.addstr(0, 0, "Search Results: ", CLR_HEADING)
        scr.addstr(0, 16, find_str, CLR_FIND)
        scr.addstr(0, 16 + len(find_str), " ctrl+X to end" +
                   " " * (curses.COLS - 31 - 12 - len(find_str)) +
                   str(start) + "-" + str(end) + " of " + str(cLogs),
                   CLR_HEADING)
    else:
        scr.addstr(0, 0, "Log Output:" + " " * (curses.COLS - 31) +
                   str(start) + "-" + str(end) + " of " + str(cLogs),
                   CLR_HEADING)
    ver = " mycroft-core " + mycroft.version.CORE_VERSION_STR + " ==="
    scr.addstr(1, 0, "=" * (curses.COLS - 1 - len(ver)), CLR_HEADING)
    scr.addstr(1, curses.COLS - 1 - len(ver), ver, CLR_HEADING)

    y = 2
    for i in range(start, end):
        if i >= cLogs - 1:
            log = '   ^--- NEWEST ---^ '
        else:
            log = filteredLog[i]
        logid = log[0]
        if len(log) > 25 and log[5] == '-' and log[8] == '-':
            log = log[11:]  # skip logid & date at the front of log line
        else:
            log = log[1:]   # just skip the logid

        # Categorize log line
        if "| DEBUG    |" in log:
            log = log.replace("Skills ", "")
            clr = CLR_LOG_DEBUG
        elif "| ERROR    |" in log:
            clr = CLR_LOG_ERROR
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
            elif end >= len_line - 1:
                log = "~~~~" + log[start:end]   # ....end
            else:
                log = "~~" + log[start:end] + "~~"  # ..middle..
        if len_line > longest_visible_line:
            longest_visible_line = len_line
        scr.addstr(y, 0, handleNonAscii(log), clr)
        y += 1

    # Log legend in the lower-right
    y_log_legend = curses.LINES - (3 + cy_chat_area)
    scr.addstr(y_log_legend, curses.COLS // 2 + 2,
               make_titlebar("Log Output Legend", curses.COLS // 2 - 2),
               CLR_HEADING)
    scr.addstr(y_log_legend + 1, curses.COLS // 2 + 2,
               "DEBUG output",
               CLR_LOG_DEBUG)
    if len(log_files) > 0:
        scr.addstr(y_log_legend + 2, curses.COLS // 2 + 2,
                   os.path.basename(log_files[0]) + ", other",
                   CLR_LOG2)
    if len(log_files) > 1:
        scr.addstr(y_log_legend + 3, curses.COLS // 2 + 2,
                   os.path.basename(log_files[1]), CLR_LOG1)

    # Meter
    y_meter = y_log_legend
    if show_meter:
        scr.addstr(y_meter, curses.COLS - 14, " Mic Level ",
                   CLR_HEADING)

    # History log in the middle
    y_chat_history = curses.LINES - (3 + cy_chat_area)
    chat_width = curses.COLS // 2 - 2
    chat_out = []
    scr.addstr(y_chat_history, 0, make_titlebar("History", chat_width),
               CLR_HEADING)

    # Build a nicely wrapped version of the chat log
    idx_chat = len(chat) - 1
    while len(chat_out) < cy_chat_area and idx_chat >= 0:
        if chat[idx_chat][0] == '>':
            wrapper = textwrap.TextWrapper(initial_indent="",
                                           subsequent_indent="   ",
                                           width=chat_width)
        else:
            wrapper = textwrap.TextWrapper(width=chat_width)

        chatlines = wrapper.wrap(chat[idx_chat])
        for txt in reversed(chatlines):
            if len(chat_out) >= cy_chat_area:
                break
            chat_out.insert(0, txt)

        idx_chat -= 1

    # Output the chat
    y = curses.LINES - (2 + cy_chat_area)
    for txt in chat_out:
        if txt.startswith(">> ") or txt.startswith("   "):
            clr = CLR_CHAT_RESP
        else:
            clr = CLR_CHAT_QUERY
        scr.addstr(y, 1, handleNonAscii(txt), clr)
        y += 1

    if show_gui and curses.COLS > 20 and curses.LINES > 20:
        _do_gui(curses.COLS - 20)

    # Command line at the bottom
    ln = line
    if len(line) > 0 and line[0] == ":":
        scr.addstr(curses.LINES - 2, 0, "Command ('help' for options):",
                   CLR_CMDLINE)
        scr.addstr(curses.LINES - 1, 0, ":", CLR_CMDLINE)
        ln = line[1:]
    else:
        prompt = "Input (':' for command, Ctrl+C to quit)"
        if show_last_key:
            prompt += " === keycode: " + last_key
        scr.addstr(curses.LINES - 2, 0,
                   make_titlebar(prompt,
                                 curses.COLS - 1),
                   CLR_HEADING)
        scr.addstr(curses.LINES - 1, 0, ">", CLR_HEADING)

    _do_meter(cy_chat_area + 2)
    scr.addstr(curses.LINES - 1, 2, ln[-(curses.COLS - 3):], CLR_INPUT)

    # Curses doesn't actually update the display until refresh() is called
    scr.refresh()


def make_titlebar(title, bar_length):
    return title + " " + ("=" * (bar_length - 1 - len(title)))

##############################################################################
# Help system


help_struct = [('Log Scrolling shortcuts',
                [("Up / Down / PgUp / PgDn",
                  "scroll thru history"),
                 ("Ctrl+T / Ctrl+PgUp",
                  "scroll to top of logs (jump to oldest)"),
                 ("Ctrl+B / Ctrl+PgDn",
                  "scroll to bottom of logs" + "(jump to newest)"),
                 ("Left / Right",
                  "scroll long lines left/right"),
                 ("Home / End",
                  "scroll to start/end of long lines")]),
               ("Query History shortcuts",
                [("Ctrl+N / Ctrl+Left",
                  "previous query"),
                 ("Ctrl+P / Ctrl+Right",
                    "next query")]),
               ("General Commands (type ':' to enter command mode)",
                [(":quit or :exit",
                  "exit the program"),
                 (":meter (show|hide)",
                    "display the microphone level"),
                    (":keycode (show|hide)",
                     "display typed key codes (mainly debugging)"),
                    (":history (# lines)",
                     "set size of visible history buffer"),
                    (":clear",
                     "flush the logs")]),
               ("Log Manipulation Commands",
                [(":filter 'STR'",
                  "adds a log filter (optional quotes)"),
                 (":filter remove 'STR'",
                    "removes a log filter"),
                    (":filter (clear|reset)",
                     "reset filters"),
                    (":filter (show|list)",
                     "display current filters"),
                    (":find 'STR'",
                     "show logs containing 'str'"),
                    (":log level (DEBUG|INFO|ERROR)",
                     "set logging level"),
                    (":log bus (on|off)",
                     "control logging of messagebus messages")]),
               ("Skill Debugging Commands",
                [(":skills",
                  "list installed Skills"),
                 (":api SKILL",
                    "show Skill's public API"),
                    (":activate SKILL",
                     "activate Skill, e.g. 'activate skill-wiki'"),
                    (":deactivate SKILL",
                     "deactivate Skill"),
                    (":keep SKILL",
                     "deactivate all Skills except the indicated Skill")])]
help_longest = 0
for s in help_struct:
    for ent in s[1]:
        help_longest = max(help_longest, len(ent[0]))


HEADER_SIZE = 2
HEADER_FOOTER_SIZE = 4


def num_help_pages():
    lines = 0
    for section in help_struct:
        lines += 3 + len(section[1])
    return ceil(lines / (curses.LINES - HEADER_FOOTER_SIZE))


def do_draw_help(scr):

    def render_header():
        scr.addstr(0, 0, center(25) + "Mycroft Command Line Help", CLR_HEADING)
        scr.addstr(1, 0, "=" * (curses.COLS - 1), CLR_HEADING)

    def render_help(txt, y_pos, i, first_line, last_line, clr):
        if i >= first_line and i < last_line:
            scr.addstr(y_pos, 0, txt, clr)
            y_pos += 1
        return y_pos

    def render_footer(page, total):
        text = "Page {} of {} [ Any key to continue ]".format(page, total)
        scr.addstr(curses.LINES - 1, 0, center(len(text)) + text, CLR_HEADING)

    scr.erase()
    render_header()
    y = HEADER_SIZE
    page = subscreen + 1

    # Find first and last taking into account the header and footer
    first = subscreen * (curses.LINES - HEADER_FOOTER_SIZE)
    last = first + (curses.LINES - HEADER_FOOTER_SIZE)
    i = 0
    for section in help_struct:
        y = render_help(section[0], y, i, first, last, CLR_HEADING)
        i += 1
        y = render_help("=" * (curses.COLS - 1), y, i, first, last,
                        CLR_HEADING)
        i += 1

        for line in section[1]:
            words = line[1].split()
            ln = line[0].ljust(help_longest + 1)
            for w in words:
                if len(ln) + 1 + len(w) < curses.COLS:
                    ln += " " + w
                else:
                    y = render_help(ln, y, i, first, last, CLR_CMDLINE)
                    ln = " ".ljust(help_longest + 2) + w
            y = render_help(ln, y, i, first, last, CLR_CMDLINE)
            i += 1

        y = render_help(" ", y, i, first, last, CLR_CMDLINE)
        i += 1

        if i > last:
            break

    render_footer(page, num_help_pages())

    # Curses doesn't actually update the display until refresh() is called
    scr.refresh()


def show_help():
    global screen_mode
    global subscreen

    if screen_mode != SCR_HELP:
        screen_mode = SCR_HELP
        subscreen = 0
        set_screen_dirty()


def show_next_help():
    global screen_mode
    global subscreen

    if screen_mode == SCR_HELP:
        subscreen += 1
        if subscreen >= num_help_pages():
            screen_mode = SCR_MAIN
        set_screen_dirty()


##############################################################################
# Skill debugging

def show_skills(skills):
    """Show list of loaded Skills in as many column as necessary."""
    global scr
    global screen_mode

    if not scr:
        return

    screen_mode = SCR_SKILLS

    row = 2
    column = 0

    def prepare_page():
        global scr
        nonlocal row
        nonlocal column
        scr.erase()
        scr.addstr(0, 0, center(25) + "Loaded Skills", CLR_CMDLINE)
        scr.addstr(1, 1, "=" * (curses.COLS - 2), CLR_CMDLINE)
        row = 2
        column = 0

    prepare_page()
    col_width = 0
    skill_names = sorted(skills.keys())
    for skill in skill_names:
        if skills[skill]['active']:
            color = curses.color_pair(4)
        else:
            color = curses.color_pair(2)

        scr.addstr(row, column, "  {}".format(skill), color)
        row += 1
        col_width = max(col_width, len(skill))
        if row == curses.LINES - 2 and column > 0 and skill != skill_names[-1]:
            column = 0
            scr.addstr(curses.LINES - 1, 0,
                       center(23) + "Press any key to continue", CLR_HEADING)
            scr.refresh()
            wait_for_any_key()
            prepare_page()
        elif row == curses.LINES - 2:
            # Reached bottom of screen, start at top and move output to a
            # New column
            row = 2
            column += col_width + 2
            col_width = 0
            if column > curses.COLS - 20:
                # End of screen
                break

    scr.addstr(curses.LINES - 1, 0, center(23) + "Press any key to return",
               CLR_HEADING)
    scr.refresh()


def show_skill_api(skill, data):
    """Show available help on Skill's API."""
    global scr
    global screen_mode

    if not scr:
        return

    screen_mode = SCR_SKILLS

    row = 2
    column = 0

    def prepare_page():
        global scr
        nonlocal row
        nonlocal column
        scr.erase()
        scr.addstr(0, 0, center(25) + "Skill-API for {}".format(skill),
                   CLR_CMDLINE)
        scr.addstr(1, 1, "=" * (curses.COLS - 2), CLR_CMDLINE)
        row = 2
        column = 4

    prepare_page()
    for key in data:
        color = curses.color_pair(4)

        scr.addstr(row, column, "{} ({})".format(key, data[key]['type']),
                   CLR_HEADING)
        row += 2
        if 'help' in data[key]:
            help_text = data[key]['help'].split('\n')
            for line in help_text:
                scr.addstr(row, column + 2, line, color)
                row += 1
            row += 2
        else:
            row += 1

        if row == curses.LINES - 5:
            scr.addstr(curses.LINES - 1, 0,
                       center(23) + "Press any key to continue", CLR_HEADING)
            scr.refresh()
            wait_for_any_key()
            prepare_page()
        elif row == curses.LINES - 5:
            # Reached bottom of screen, start at top and move output to a
            # New column
            row = 2

    scr.addstr(curses.LINES - 1, 0, center(23) + "Press any key to return",
               CLR_HEADING)
    scr.refresh()


def center(str_len):
    # generate number of characters needed to center a string
    # of the given length
    return " " * ((curses.COLS - str_len) // 2)


##############################################################################
# Main UI lopo

def _get_cmd_param(cmd, keyword):
    # Returns parameter to a command.  Will de-quote.
    # Ex: find 'abc def'   returns: abc def
    #    find abc def     returns: abc def
    if isinstance(keyword, list):
        for w in keyword:
            cmd = cmd.replace(w, "").strip()
    else:
        cmd = cmd.replace(keyword, "").strip()
    if not cmd:
        return None

    last_char = cmd[-1]
    if last_char == '"' or last_char == "'":
        parts = cmd.split(last_char)
        return parts[-2]
    else:
        parts = cmd.split(" ")
        return parts[-1]


def wait_for_any_key():
    """Block until key is pressed.

    This works around curses.error that can occur on old versions of ncurses.
    """
    while True:
        try:
            scr.get_wch()  # blocks
        except curses.error:
            # Loop if get_wch throws error
            time.sleep(0.05)
        else:
            break


def handle_cmd(cmd):
    global show_meter
    global screen_mode
    global log_filters
    global cy_chat_area
    global find_str
    global show_last_key

    if "show" in cmd and "log" in cmd:
        pass
    elif "help" in cmd:
        show_help()
    elif "exit" in cmd or "quit" in cmd:
        return 1
    elif "keycode" in cmd:
        # debugging keyboard
        if "hide" in cmd or "off" in cmd:
            show_last_key = False
        elif "show" in cmd or "on" in cmd:
            show_last_key = True
    elif "meter" in cmd:
        # microphone level meter
        if "hide" in cmd or "off" in cmd:
            show_meter = False
        elif "show" in cmd or "on" in cmd:
            show_meter = True
    elif "find" in cmd:
        find_str = _get_cmd_param(cmd, "find")
        rebuild_filtered_log()
    elif "filter" in cmd:
        if "show" in cmd or "list" in cmd:
            # display active filters
            add_log_message("Filters: " + str(log_filters))
            return

        if "reset" in cmd or "clear" in cmd:
            log_filters = list(default_log_filters)
        else:
            # extract last word(s)
            param = _get_cmd_param(cmd, "filter")
            if param:
                if "remove" in cmd and param in log_filters:
                    log_filters.remove(param)
                else:
                    log_filters.append(param)

        rebuild_filtered_log()
        add_log_message("Filters: " + str(log_filters))
    elif "clear" in cmd:
        clear_log()
    elif "log" in cmd:
        # Control logging behavior in all Mycroft processes
        if "level" in cmd:
            level = _get_cmd_param(cmd, ["log", "level"])
            bus.emit(Message("mycroft.debug.log", data={'level': level}))
        elif "bus" in cmd:
            state = _get_cmd_param(cmd, ["log", "bus"]).lower()
            if state in ["on", "true", "yes"]:
                bus.emit(Message("mycroft.debug.log", data={'bus': True}))
            elif state in ["off", "false", "no"]:
                bus.emit(Message("mycroft.debug.log", data={'bus': False}))
    elif "history" in cmd:
        # extract last word(s)
        lines = int(_get_cmd_param(cmd, "history"))
        if not lines or lines < 1:
            lines = 1
        max_chat_area = curses.LINES - 7
        if lines > max_chat_area:
            lines = max_chat_area
        cy_chat_area = lines
    elif "skills" in cmd:
        # List loaded skill
        message = bus.wait_for_response(
            Message('skillmanager.list'), reply_type='mycroft.skills.list')

        if message:
            show_skills(message.data)
            wait_for_any_key()

            screen_mode = SCR_MAIN
            set_screen_dirty()
    elif "deactivate" in cmd:
        skills = cmd.split()[1:]
        if len(skills) > 0:
            for s in skills:
                bus.emit(Message("skillmanager.deactivate", data={'skill': s}))
        else:
            add_log_message('Usage :deactivate SKILL [SKILL2] [...]')
    elif "keep" in cmd:
        s = cmd.split()
        if len(s) > 1:
            bus.emit(Message("skillmanager.keep", data={'skill': s[1]}))
        else:
            add_log_message('Usage :keep SKILL')

    elif "activate" in cmd:
        skills = cmd.split()[1:]
        if len(skills) > 0:
            for s in skills:
                bus.emit(Message("skillmanager.activate", data={'skill': s}))
        else:
            add_log_message('Usage :activate SKILL [SKILL2] [...]')
    elif "api" in cmd:
        parts = cmd.split()
        if len(parts) < 2:
            return
        skill = parts[1]
        message = bus.wait_for_response(Message('{}.public_api'.format(skill)))
        if message:
            show_skill_api(skill, message.data)
            scr.get_wch()  # blocks
            screen_mode = SCR_MAIN
            set_screen_dirty()

    # TODO: More commands
    return 0  # do nothing upon return


def handle_is_connected(msg):
    add_log_message("Connected to Messagebus!")
    # start_qml_gui(bus, gui_text)


def handle_reconnecting():
    add_log_message("Looking for Messagebus websocket...")


def gui_main(stdscr):
    global scr
    global bus
    global line
    global log_line_lr_scroll
    global longest_visible_line
    global find_str
    global last_key
    global history
    global screen_lock
    global show_gui
    global config

    scr = stdscr
    init_screen()
    scr.keypad(1)
    scr.notimeout(True)

    bus.on('speak', handle_speak)
    bus.on('message', handle_message)
    bus.on('recognizer_loop:utterance', handle_utterance)
    bus.on('connected', handle_is_connected)
    bus.on('reconnecting', handle_reconnecting)

    add_log_message("Establishing Mycroft Messagebus connection...")

    gui_thread = ScreenDrawThread()
    gui_thread.setDaemon(True)  # this thread won't prevent prog from exiting
    gui_thread.start()

    hist_idx = -1  # index, from the bottom
    c = 0
    try:
        while True:
            set_screen_dirty()
            c = 0
            code = 0

            try:
                if ctrl_c_pressed():
                    # User hit Ctrl+C. treat same as Ctrl+X
                    c = 24
                else:
                    # Don't block, this allows us to refresh the screen while
                    # waiting on initial messagebus connection, etc
                    scr.timeout(1)
                    c = scr.get_wch()   # unicode char or int for special keys
                    if c == -1:
                        continue
            except curses.error:
                # This happens in odd cases, such as when you Ctrl+Z
                # the CLI and then resume.  Curses fails on get_wch().
                continue

            if isinstance(c, int):
                code = c
            else:
                code = ord(c)

            # Convert VT100 ESC codes generated by some terminals
            if code == 27:
                # NOTE:  Not sure exactly why, but the screen can get corrupted
                # if we draw to the screen while doing a scr.getch().  So
                # lock screen updates until the VT100 sequence has been
                # completely read.
                with screen_lock:
                    scr.timeout(0)
                    c1 = -1
                    start = time.time()
                    while c1 == -1:
                        c1 = scr.getch()
                        if time.time() - start > 1:
                            break  # 1 second timeout waiting for ESC code

                    c2 = -1
                    while c2 == -1:
                        c2 = scr.getch()
                        if time.time() - start > 1:  # 1 second timeout
                            break  # 1 second timeout waiting for ESC code

                if c1 == 79 and c2 == 120:
                    c = curses.KEY_UP
                elif c1 == 79 and c2 == 116:
                    c = curses.KEY_LEFT
                elif c1 == 79 and c2 == 114:
                    c = curses.KEY_DOWN
                elif c1 == 79 and c2 == 118:
                    c = curses.KEY_RIGHT
                elif c1 == 79 and c2 == 121:
                    c = curses.KEY_PPAGE  # aka PgUp
                elif c1 == 79 and c2 == 115:
                    c = curses.KEY_NPAGE  # aka PgDn
                elif c1 == 79 and c2 == 119:
                    c = curses.KEY_HOME
                elif c1 == 79 and c2 == 113:
                    c = curses.KEY_END
                else:
                    c = c1

                if c1 != -1:
                    last_key = str(c) + ",ESC+" + str(c1) + "+" + str(c2)
                    code = c
                else:
                    last_key = "ESC"
            else:
                if code < 33:
                    last_key = str(code)
                else:
                    last_key = str(code)

            scr.timeout(-1)   # resume blocking
            if code == 27:    # Hitting ESC twice clears the entry line
                hist_idx = -1
                line = ""
            elif c == curses.KEY_RESIZE:
                # Generated by Curses when window/screen has been resized
                y, x = scr.getmaxyx()
                curses.resizeterm(y, x)

                # resizeterm() causes another curses.KEY_RESIZE, so
                # we need to capture that to prevent a loop of resizes
                c = scr.get_wch()
            elif screen_mode == SCR_HELP:
                # in Help mode, any key goes to next page
                show_next_help()
                continue
            elif c == '\n' or code == 10 or code == 13 or code == 343:
                # ENTER sends the typed line to be processed by Mycroft
                if line == "":
                    continue

                if line[:1] == ":":
                    # Lines typed like ":help" are 'commands'
                    if handle_cmd(line[1:]) == 1:
                        break
                else:
                    # Treat this as an utterance
                    bus.emit(Message("recognizer_loop:utterance",
                                     {'utterances': [line.strip()],
                                      'lang': config.get('lang', 'en-us')},
                                     {'client_name': 'mycroft_cli',
                                      'source': 'debug_cli',
                                      'destination': ["skills"]}
                                     ))
                hist_idx = -1
                line = ""
            elif code == 16 or code == 545:  # Ctrl+P or Ctrl+Left (Previous)
                # Move up the history stack
                hist_idx = clamp(hist_idx + 1, -1, len(history) - 1)
                if hist_idx >= 0:
                    line = history[len(history) - hist_idx - 1]
                else:
                    line = ""
            elif code == 14 or code == 560:  # Ctrl+N or Ctrl+Right (Next)
                # Move down the history stack
                hist_idx = clamp(hist_idx - 1, -1, len(history) - 1)
                if hist_idx >= 0:
                    line = history[len(history) - hist_idx - 1]
                else:
                    line = ""
            elif c == curses.KEY_LEFT:
                # scroll long log lines left
                log_line_lr_scroll += curses.COLS // 4
            elif c == curses.KEY_RIGHT:
                # scroll long log lines right
                log_line_lr_scroll -= curses.COLS // 4
                if log_line_lr_scroll < 0:
                    log_line_lr_scroll = 0
            elif c == curses.KEY_HOME:
                # HOME scrolls log lines all the way to the start
                log_line_lr_scroll = longest_visible_line
            elif c == curses.KEY_END:
                # END scrolls log lines all the way to the end
                log_line_lr_scroll = 0
            elif c == curses.KEY_UP:
                scroll_log(False, 1)
            elif c == curses.KEY_DOWN:
                scroll_log(True, 1)
            elif c == curses.KEY_NPAGE:  # aka PgDn
                # PgDn to go down a page in the logs
                scroll_log(True)
            elif c == curses.KEY_PPAGE:  # aka PgUp
                # PgUp to go up a page in the logs
                scroll_log(False)
            elif code == 2 or code == 550:  # Ctrl+B or Ctrl+PgDn
                scroll_log(True, max_log_lines)
            elif code == 20 or code == 555:  # Ctrl+T or Ctrl+PgUp
                scroll_log(False, max_log_lines)
            elif code == curses.KEY_BACKSPACE or code == 127:
                # Backspace to erase a character in the utterance
                line = line[:-1]
            elif code == 6:  # Ctrl+F (Find)
                line = ":find "
            elif code == 7:  # Ctrl+G (start GUI)
                if show_gui is None:
                    start_qml_gui(bus, gui_text)
                show_gui = not show_gui
            elif code == 18:  # Ctrl+R (Redraw)
                scr.erase()
            elif code == 24:  # Ctrl+X (Exit)
                if find_str:
                    # End the find session
                    find_str = None
                    rebuild_filtered_log()
                elif line.startswith(":"):
                    # cancel command mode
                    line = ""
                else:
                    # exit CLI
                    break
            elif code > 31 and isinstance(c, str):
                # Accept typed character in the utterance
                line += c

    finally:
        scr.erase()
        scr.refresh()
        scr = None


def simple_cli():
    global bSimple
    bSimple = True

    bus.on('speak', handle_speak)
    try:
        while True:
            # Sleep for a while so all the output that results
            # from the previous command finishes before we print.
            time.sleep(1.5)
            print("Input (Ctrl+C to quit):")
            line = sys.stdin.readline()
            bus.emit(Message("recognizer_loop:utterance",
                             {'utterances': [line.strip()]},
                             {'client_name': 'mycroft_simple_cli',
                              'source': 'debug_cli',
                              'destination': ["skills"]}))
    except KeyboardInterrupt as e:
        # User hit Ctrl+C to quit
        print("")
    except KeyboardInterrupt as e:
        LOG.exception(e)
        event_thread.exit()
        sys.exit()


def connect_to_messagebus():
    """ Connect to the mycroft messagebus and launch a thread handling the
        connection.

        Returns: WebsocketClient
    """
    bus = MessageBusClient()  # Mycroft messagebus connection

    event_thread = Thread(target=connect, args=[bus])
    event_thread.setDaemon(True)
    event_thread.start()
    return bus
