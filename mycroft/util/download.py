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
from threading import Thread

import os
import requests
from os.path import exists, dirname
import subprocess

_running_downloads = {}


def _get_download_tmp(dest):
    tmp_base = dest + '.part'
    if not exists(tmp_base):
        return tmp_base
    else:
        i = 1
        while(True):
            tmp = tmp_base + '.' + str(i)
            if not exists(tmp):
                return tmp
            else:
                i += 1


class Downloader(Thread):
    """
        Downloader is a thread based downloader instance when instanciated
        it will download the provided url to a file on disk.

        When the download is complete or failed the `.done` property will
        be set to true and the `.status` will indicate the status code.
        200 = Success.

        Args:
            url:            Url to download
            dest:           Path to save data to
            complet_action: Function to run when download is complete.
                            `func(dest)`
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
        if not exists(dirname(dest)):
            os.makedirs(dirname(dest))

        #  Start thread
        self.daemon = True
        self.start()

    def perform_download(self, dest):

        cmd = ['wget', '-c', self.url, '-O', dest,
               '--tries=20', '--read-timeout=5']
        if self.header:
            cmd += ['--header={}'.format(self.header)]
        return subprocess.call(cmd)

    def run(self):
        """
            Does the actual download.
        """
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
        """
            Move the .part file to the final destination and perform any
            actions that should be performed at completion.
        """
        os.rename(tmp, self.dest)
        if self.complete_action:
            self.complete_action(self.dest)

    def cleanup(self, tmp):
        """
            Cleanup after download attempt
        """
        if exists(tmp):
            os.remove(self.dest + '.part')
        if self.status == 200:
            self.status = -1

    def abort(self):
        """
            Abort download process
        """
        self._abort = True


def download(url, dest, complete_action=None, header=None):
    global _running_downloads
    arg_hash = hash(url + dest)
    if arg_hash not in _running_downloads:
        _running_downloads[arg_hash] = Downloader(url, dest, complete_action,
                                                  header)
    return _running_downloads[arg_hash]
