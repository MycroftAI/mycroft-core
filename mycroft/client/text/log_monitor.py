from os import stat
from pathlib import Path
from threading import Thread

from mycroft.configuration import Configuration


class LogMonitorThread(Thread):
    def __init__(self, filename, logid):
        super().__init__()
        self.filename = filename
        self.st_results = stat(filename)
        self.logid = str(logid)

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


def get_log_file_paths(config):
    log_dir_config = config.get('log_dir')
    if log_dir_config is None:
        log_dir = Path("/var/log/mycroft")
    else:
        log_dir = Path.home().joinpath(log_dir_config)
    log_file_paths = [
        log_dir.joinpath("skills.log"), log_dir.joinpath("voice.log")
    ]

    return log_file_paths


def start_log_monitors():
    # Monitor system logs
    # this thread won't prevent prog from exiting
    config = Configuration.get()
    log_file_paths = get_log_file_paths(config)
    for log_file_path in log_file_paths:
        if log_file_path.is_file():
            thread = LogMonitorThread(log_file_path, len(log_file_paths))
            thread.setDaemon(True)
            thread.start()
