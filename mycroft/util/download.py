from threading import Thread
import requests
import os
from os.path import exists

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
    def __init__(self, url, dest, complete_action=None):
        super(Downloader, self).__init__()
        self.url = url
        self.dest = dest
        self.complete_action = complete_action
        self.status = None
        self.done = False
        self._abort = False

        #  Start thread
        self.start()

    def run(self):
        """
            Does the actual download.
        """
        r = requests.get(self.url, stream=True)
        tmp = _get_download_tmp(self.dest)
        with open(tmp, 'w') as f:
            for chunk in r.iter_content():
                f.write(chunk)
                if self._abort:
                    break

        self.status = r.status_code
        if not self._abort and self.status == 200:
            self.finalize(tmp)
        else:
            self.cleanup(self, tmp)
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

    def cleanup(tmp):
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


def download(url, dest, complete_action=None):
    global _running_downloads
    arg_hash = hash(url + dest)
    if arg_hash not in _running_downloads:
        _running_downloads[arg_hash] = Downloader(url, dest, complete_action)
    return _running_downloads[arg_hash]
