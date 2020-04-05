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
"""Download utility based on wget.

The utility is a real simple implementation leveraging the wget command line
application supporting resume on failed download.
"""
from glob import glob
import os
from os.path import exists, dirname
import subprocess
from threading import Thread

from .file_utils import ensure_directory_exists

_running_downloads = {}  # Cache of running downloads


def _get_download_tmp(dest):
    """Get temporary file for download.

    Arguments:
        dest (str): path to download location

    Returns:
        (str) path to temporary download location
    """
    tmp_base = dest + '.part'
    existing = glob(tmp_base + '*')
    if len(existing) > 0:
        return '{}.{}'.format(tmp_base, len(existing))
    else:
        return tmp_base


class Downloader(Thread):
    """Simple file downloader.

    Downloader is a thread based downloader instance when instanciated
    it will download the provided url to a file on disk.

    When the download is complete or failed the `.done` property will
    be set to true and the `.status` will indicate the HTTP status code.
    200 = Success.

    Arguments:
        url (str): Url to download
        dest (str): Path to save data to
        complete_action (callable): Function to run when download is complete
                                    `func(dest)`
        header: any special header needed for starting the transfer
    """

    def __init__(self, url, dest, complete_action=None, header=None):
        super(Downloader, self).__init__()
        self.url = url
        self.dest = dest
        self.complete_action = complete_action
        self.status = None
        self.done = False
        self._abort = False
        self.header = header

        # Create directories as needed
        ensure_directory_exists(dirname(dest), permissions=0o775)

        #  Start thread
        self.daemon = True
        self.start()

    def perform_download(self, dest):
        """Handle the download through wget.

        Arguments:
            dest (str): Save location
        """
        cmd = ['wget', '-c', self.url, '-O', dest,
               '--tries=20', '--read-timeout=5']
        if self.header:
            cmd += ['--header={}'.format(self.header)]
        return subprocess.call(cmd)

    def run(self):
        """Do the actual download."""
        tmp = _get_download_tmp(self.dest)
        self.status = self.perform_download(tmp)
        if not self._abort and self.status == 0:
            self.finalize(tmp)
        else:
            self.cleanup(tmp)
        self.done = True
        arg_hash = hash(self.url + self.dest)

        #  Remove from list of currently running downloads
        if arg_hash in _running_downloads:
            _running_downloads.pop(arg_hash)

    def finalize(self, tmp):
        """Move temporary download data to final location.

        Move the .part file to the final destination and perform any
        actions that should be performed at completion.

        Arguments:
            tmp(str): temporary file path
        """
        os.rename(tmp, self.dest)
        if self.complete_action:
            self.complete_action(self.dest)

    def cleanup(self, tmp):
        """Cleanup after download attempt."""
        if exists(tmp):
            os.remove(self.dest + '.part')
        if self.status == 200:
            self.status = -1

    def abort(self):
        """Abort download process."""
        self._abort = True


def download(url, dest, complete_action=None, header=None):
    """Start a download or fetch an already running.

    Arguments:
        url (str): url to download
        dest (str): path to save download to
        complete_action (callable): Optional function to call on completion
        header (str): Optional header to use for the download

    Returns:
        Downloader object
    """
    global _running_downloads
    arg_hash = hash(url + dest)
    if arg_hash not in _running_downloads:
        _running_downloads[arg_hash] = Downloader(url, dest, complete_action,
                                                  header)
    return _running_downloads[arg_hash]
