from argparse import ArgumentParser
from datetime import date, datetime, time
from locale import localeconv
from pathlib import Path

BOOT_START_MESSAGE = 'Starting message bus service...'
BOOT_END_MESSAGE = 'Skills all loaded!'
NOT_FOUND = -1
TIME_FORMAT = '%Y-%m-%d %H:%M:%S{}%f'.format(localeconv()['decimal_point'])


class LogFileReader:
    log_dir = Path('/var/log/mycroft')

    def __init__(self, log_name):
        self.log_name = log_name
        self.log_path = self.log_dir.joinpath(log_name + '.log')
        self.log_file = None
        self.log_file_rec = None
        self.log_msg = None
        self.log_msg_ts = None
        self.log_msg_lines = []
        self.eof = False

    def read_log_msg(self):
        still_reading_log_msg = True
        while still_reading_log_msg:
            self.log_file_rec = self.log_file.readline().rstrip()
            if self.log_file_rec:
                still_reading_log_msg = self._process_log_file_rec()
            else:
                self.eof = True
                still_reading_log_msg = False

    def _process_log_file_rec(self):
        still_reading_log_message = True
        split_rec = self.log_file_rec.split(' | ')
        log_msg_first_line = len(split_rec) == 5
        if log_msg_first_line:
            if self.log_msg_lines:
                self.log_msg = '\n'.join(self.log_msg_lines)
                self.log_msg_lines = []
                still_reading_log_message = False
            self._reformat_log_msg(split_rec)
            self._parse_log_msg_ts(split_rec[0])
        self.log_msg_lines.append(self.log_file_rec)

        return still_reading_log_message

    def _reformat_log_msg(self, log_msg_parts):
        reformatted_parts = []
        process = '{:10}'.format(self.log_name)
        for index, part in enumerate(log_msg_parts):
            if index == 2:
                reformatted_parts.append(process)
            elif index == 3:
                if part.find(':') == NOT_FOUND:
                    reformatted_parts.append(part)
                else:
                    module = part[:part.find(':')]
                    reformatted_parts.append(module)
            else:
                reformatted_parts.append(part)

        self.log_file_rec = ' | '.join(reformatted_parts)

    def _parse_log_msg_ts(self, log_msg_ts):
        try:
            self.log_msg_ts = datetime.strptime(log_msg_ts, TIME_FORMAT)
        except ValueError:
            print(
                'Found log message with bad time section: ' + self.log_file_rec
            )

    def check_for_inclusion(self, earliest_ts, script_args):
        emitted_after_start_ts = self.log_msg_ts > earliest_ts
        matches_inclusion_string = (
            script_args.include is not None and
            any([i in self.log_msg for i in script_args.include])
        )
        matches_exclusion_string = (
            script_args.exclude is not None and
            any([e in self.log_msg for e in script_args.exclude])
        )
        msg_parts = self.log_msg.split(' | ')
        process = None if len(msg_parts) < 3 else msg_parts[2].strip()
        include_process = (
            script_args.process is None or
            (process is not None and process == script_args.process)
        )

        return (
            emitted_after_start_ts and
            (script_args.include is None or matches_inclusion_string) and
            (script_args.exclude is None or not matches_exclusion_string) and
            include_process
        )


class LogWriter:
    def __init__(self, script_args):
        self.script_args = script_args
        self.start_ts = datetime.combine(
            script_args.start_date,
            script_args.start_time
        )
        self.log_readers = [
            LogFileReader('skills'),
            LogFileReader('audio'),
            LogFileReader('bus'),
            LogFileReader('enclosure'),
            LogFileReader('voice')
        ]
        self.merged_log_file = None
        self.in_boot_process = False
        self.boot_logs_complete = False
        self.boot_logs = []

    def run(self):
        self._open_files()
        try:
            for log_message in self.merge_logs():
                include = self._check_inclusion_criteria(log_message)
                if self.script_args.last_boot:
                    self._check_for_boot_start(log_message)
                    self._add_to_boot_logs(log_message, include)
                    self._check_for_boot_end(log_message)
                else:
                    if include:
                        self._write_log_message(log_message)

            if self.script_args.last_boot:
                if self.boot_logs_complete:
                    for log_message in self.boot_logs:
                        self._write_log_message(log_message)
                else:
                    self._write_log_message('Boot sequence not finished.')
        finally:
            self._close_files()

    def _open_files(self):
        for log_reader in self.log_readers:
            log_reader.log_file = open(str(log_reader.log_path))
        if self.script_args.file is not None:
            self.merged_log_file = open(self.script_args.file, 'w')

    def _close_files(self):
        for log_reader in self.log_readers:
            log_reader.log_file.close()
        if self.script_args.file is not None:
            self.merged_log_file.close()

    def merge_logs(self):
        for log_reader in self.log_readers:
            log_reader.read_log_msg()

        while not all([reader.eof for reader in self.log_readers]):
            next_message_ts = min(
                [r.log_msg_ts for r in self.log_readers if not r.eof]
            )
            for log_reader in self.log_readers:
                if log_reader.log_msg_ts == next_message_ts:
                    if log_reader.log_msg_ts > self.start_ts:
                        yield log_reader.log_msg
                    log_reader.read_log_msg()

    def _check_for_boot_start(self, log_msg):
        if not self.in_boot_process and self.script_args.last_boot:
            msg_parts = log_msg.split(' | ')
            if msg_parts[-1].strip() == BOOT_START_MESSAGE:
                self.in_boot_process = True

    def _check_for_boot_end(self, log_msg):
        if self.in_boot_process and self.script_args.last_boot:
            msg_parts = log_msg.split(' | ')
            if msg_parts[-1].strip() == BOOT_END_MESSAGE:
                self.in_boot_process = False

    def _check_inclusion_criteria(self, log_msg):
        msg_parts = log_msg.split(' | ')
        include = (
            self.script_args.include is None or
            any([i in log_msg for i in self.script_args.include])
        )
        if self.script_args.last_boot:
            first_boot_message = msg_parts[-1] == BOOT_START_MESSAGE
            last_boot_message = msg_parts[-1] == BOOT_END_MESSAGE
            if first_boot_message or last_boot_message:
                include = True
        exclude = (
            self.script_args.exclude is not None and
            any([e in log_msg for e in self.script_args.exclude])
        )
        process = None if len(msg_parts) < 3 else msg_parts[2].strip()
        process_match = (
            self.script_args.process is None or
            (process is not None and process == self.script_args.process)
        )

        return include and not exclude and process_match

    def _add_to_boot_logs(self, log_message, include):
        if self.in_boot_process:
            self.boot_logs_complete = False
            if include:
                self.boot_logs.append(log_message)
        else:
            if self.boot_logs:
                self.boot_logs_complete = True

    def _write_log_message(self, log_msg):
        if self.script_args.file is None:
            print(log_msg)
        else:
            self.merged_log_file.write(log_msg + '\n')


def _define_script_args():
    arg_parser = ArgumentParser()
    arg_parser.add_argument(
        "--start-date",
        help='Date log messages were emitted in YYYY-MM-DD format',
        default=date.today(),
        type=lambda dt: datetime.strptime(dt, '%Y-%m-%d').date()
    )
    arg_parser.add_argument(
        "--start-time",
        default=time(0),
        help=(
            'Time log messages were emitted format in HH:MM:SS format, '
            'combined with --start-date'
        ),
        type=lambda tm: datetime.strptime(tm, '%H:%M:%S').time()
    )
    arg_parser.add_argument(
        "--include",
        action='append',
        help=(
            'Only show log messages containing this string.  If this argument '
            'is specified multiple times, log messages that match any of the '
            'values will be included'
        ),
        type=str
    )
    arg_parser.add_argument(
        "--exclude",
        action='append',
        help=(
            'Do not show log messages containing this string.  If this '
            'argument is specified multiple times, log messages that match '
            'any of the values will be excluded'
        ),
        type=str
    )
    arg_parser.add_argument(
        "--process",
        help='Show only the logs for the specified process',
        type=str
    )
    arg_parser.add_argument(
        "--last-boot",
        action='store_true',
        default=False,
        help='Show logs emitted during the last boot process.'
    )
    arg_parser.add_argument(
        "--file",
        help=(
            'Name of file log messages will be written to.  Log messages '
            'will be written to STDOUT if this argument is not specified'
        )
    )

    return arg_parser.parse_args()


if __name__ == '__main__':
    options = _define_script_args()
    log_writer = LogWriter(options)
    log_writer.run()
