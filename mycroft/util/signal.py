import os
import os.path
import tempfile
import mycroft
import time
from mycroft.util.log import getLogger

LOG = getLogger(__name__)


def get_ipc_directory(domain=None):
    """Get the directory used for Inter Process Communication

    Files in this folder can be accessed by different processes on the
    machine.  Useful for communication.  This is often a small RAM disk.

    Args:
        domain (str): The IPC domain.  Basically a subdirectory to prevent
            overlapping signal filenames.

    Returns:
        str: a path to the IPC directory
    """
    config = mycroft.configuration.ConfigurationManager.instance()
    dir = config.get("ipc_path")
    if not dir:
        # If not defined, use /tmp/mycroft/ipc
        dir = os.path.join(tempfile.gettempdir(), "mycroft", "ipc")
    return ensure_directory_exists(dir, domain)


def ensure_directory_exists(dir, domain=None):
    """ Create a directory and give access rights to all

    Args:
        domain (str): The IPC domain.  Basically a subdirectory to prevent
            overlapping signal filenames.

    Returns:
        str: a path to the directory
    """
    if domain:
        dir = os.path.join(dir, domain)
    dir = os.path.normpath(dir)

    if not os.path.isdir(dir):
        try:
            save = os.umask(0)
            os.makedirs(dir, 0777)  # give everyone rights to r/w here
        except OSError:
            LOG.warn("Failed to create: " + dir)
            pass
        finally:
            os.umask(save)

    return dir


def create_file(filename):
    """ Create the file filename and create any directories needed

        Args:
            filename: Path to the file to be created
    """
    try:
        os.makedirs(os.path.dirname(filename))
    except OSError:
        pass
    with open(filename, 'w') as f:
        f.write('')


def create_signal(signal_name):
    """Create a named signal

    Args:
        signal_name (str): The signal's name.  Must only contain characters
            valid in filenames.
    """
    try:
        path = os.path.join(get_ipc_directory(), "signal", signal_name)
        create_file(path)
        return os.path.isfile(path)
    except IOError:
        return False


def check_for_signal(signal_name, sec_lifetime=0):
    """See if a named signal exists

    Args:
        signal_name (str): The signal's name.  Must only contain characters
            valid in filenames.
        sec_lifetime (int, optional): How many seconds the signal should
            remain valid.  If 0 or not specified, it is a single-use signal.
            If -1, it never expires.

    Returns:
        bool: True if the signal is defined, False otherwise
    """
    path = os.path.join(get_ipc_directory(), "signal", signal_name)
    if os.path.isfile(path):
        if sec_lifetime == 0:
            # consume this single-use signal
            os.remove(path)
        elif sec_lifetime == -1:
            return True
        elif int(os.path.getctime(path) + sec_lifetime) < int(time.time()):
            # remove once expired
            os.remove(path)
            return False
        return True

    # No such signal exists
    return False
