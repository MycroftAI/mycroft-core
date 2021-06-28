# Copyright 2020 Mycroft AI Inc.
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
"""Mycroft file utils.

This module contains functions handling mycroft resource files and things like
accessing and curating mycroft's cache.
"""

import os
import psutil
import tempfile
from pathlib import Path
from stat import S_ISREG, ST_MTIME, ST_MODE, ST_SIZE
from typing import List

import mycroft.configuration
from .log import LOG


def resolve_resource_file(res_name):
    """Convert a resource into an absolute filename.

    Resource names are in the form: 'filename.ext'
    or 'path/filename.ext'

    The system wil look for ~/.mycroft/res_name first, and
    if not found will look at /opt/mycroft/res_name,
    then finally it will look for res_name in the 'mycroft/res'
    folder of the source code package.

    Example:
        With mycroft running as the user 'bob', if you called
        ``resolve_resource_file('snd/beep.wav')``
        it would return either:
        '/home/bob/.mycroft/snd/beep.wav' or
        '/opt/mycroft/snd/beep.wav' or
        '.../mycroft/res/snd/beep.wav'
        where the '...' is replaced by the path
        where the package has been installed.

    Args:
        res_name (str): a resource path/name

    Returns:
        (str) path to resource or None if no resource found
    """
    config = mycroft.configuration.Configuration.get()

    # First look for fully qualified file (e.g. a user setting)
    if os.path.isfile(res_name):
        return res_name

    # Now look for ~/.mycroft/res_name (in user folder)
    filename = os.path.expanduser("~/.mycroft/" + res_name)
    if os.path.isfile(filename):
        return filename

    # Next look for /opt/mycroft/res/res_name
    data_dir = os.path.join(os.path.expanduser(config['data_dir']), 'res')
    filename = os.path.expanduser(os.path.join(data_dir, res_name))
    if os.path.isfile(filename):
        return filename

    # Finally look for it in the source package
    filename = os.path.join(os.path.dirname(__file__), '..', 'res', res_name)
    filename = os.path.abspath(os.path.normpath(filename))
    if os.path.isfile(filename):
        return filename

    return None  # Resource cannot be resolved


def read_stripped_lines(filename):
    """Read a file and return a list of stripped lines.

    Args:
        filename (str): path to file to read.

    Returns:
        (list) list of lines stripped from leading and ending white chars.
    """
    with open(filename, 'r') as f:
        for line in f:
            line = line.strip()
            if line:
                yield line


def read_dict(filename, div='='):
    """Read file into dict.

    A file containing:
        foo = bar
        baz = bog

    results in a dict
    {
        'foo': 'bar',
        'baz': 'bog'
    }

    Args:
        filename (str):   path to file
        div (str): deviders between dict keys and values

    Returns:
        (dict) generated dictionary
    """
    d = {}
    with open(filename, 'r') as f:
        for line in f:
            key, val = line.split(div)
            d[key.strip()] = val.strip()
    return d


def mb_to_bytes(size):
    """Takes a size in MB and returns the number of bytes.

    Args:
        size(int/float): size in Mega Bytes

    Returns:
        (int/float) size in bytes
    """
    return size * 1024 * 1024


def _get_cache_entries(directory):
    """Get information tuple for all regular files in directory.

    Args:
        directory (str): path to directory to check

    Returns:
        (tuple) (modification time, size, filepath)
    """
    entries = (os.path.join(directory, fn) for fn in os.listdir(directory))
    entries = ((os.stat(path), path) for path in entries)

    # leave only regular files, insert modification date
    return ((stat[ST_MTIME], stat[ST_SIZE], path)
            for stat, path in entries if S_ISREG(stat[ST_MODE]))


def _delete_oldest(entries, bytes_needed):
    """Delete files with oldest modification date until space is freed.

    Args:
        entries (tuple): file + file stats tuple
        bytes_needed (int): disk space that needs to be freed

    Returns:
        (list) all removed paths
    """
    deleted_files = []
    space_freed = 0
    for moddate, fsize, path in sorted(entries):
        try:
            os.remove(path)
            space_freed += fsize
            deleted_files.append(path)
        except Exception:
            pass

        if space_freed > bytes_needed:
            break  # deleted enough!

    return deleted_files


def reduce_cache_to_limits(directory: str, limits: dict) -> List[str]:
    """Reduce cache size if any cache limits are exceeded.

    Args:
        directory: directory path that holds cached files
        limits: set of limitations for the cache size.
                May include one or more of the following values as floats:
                - min_free_disk_percent
                - min_free_disk_space
                - max_usage_disk_percent
                - max_usage_disk_space

    Returns:
        List of deleted file paths
    """
    # TODO: Consider adding more options, like whitelisted files, etc.
    deleted_files = []
    bytes_needed = 0

    def update_bytes_needed(new_bytes_needed):
        if new_bytes_needed > bytes_needed:
            bytes_needed = new_bytes_needed

    # Get disk and directory usage
    space = psutil.disk_usage(directory)
    percent_free = 100.0 - space.percent
    cache_usage_disk_space = get_directory_size(directory)
    cache_usage_disk_percent = cache_usage_disk_space / space.total

    # Check each limit if it exists and update bytes needed
    min_free_disk_percent = limits.get("min_free_disk_percent")
    if (min_free_disk_percent is not None and
            percent_free < min_free_disk_percent):
        percent_needed = min_free_disk_percent - percent_free
        update_bytes_needed(percent_needed / 100.0 * space.total)

    min_free_disk_space = limits.get("min_free_disk_space")
    if (min_free_disk_space is not None and
            space.free < min_free_disk_space):
        min_free_disk_space = mb_to_bytes(min_free_disk_space)
        update_bytes_needed(min_free_disk_space - space.free)

    max_usage_disk_percent = limits.get("max_usage_disk_percent")
    if (max_usage_disk_percent is not None and
            cache_usage_disk_percent > max_usage_disk_percent):
        percent_needed = cache_usage_disk_percent - max_usage_disk_percent
        update_bytes_needed(percent_needed / 100.0 * space.total)

    max_usage_disk_space = limits.get("max_usage_disk_space")
    if (max_usage_disk_space is not None and
            cache_usage_disk_space > max_usage_disk_space):
        max_usage_disk_space = mb_to_bytes(max_usage_disk_space)
        update_bytes_needed(cache_usage_disk_space - max_usage_disk_space)

    # Finally, delete files to free up any bytes_needed
    if bytes_needed > 0:
        update_bytes_needed(int(bytes_needed + 1.0))
        LOG.info(f"Cache exceeded limits: removing {bytes_needed} bytes")

        # get all entries in the directory w/ stats
        entries = _get_cache_entries(directory)
        # delete as many as needed starting with the oldest
        deleted_files = _delete_oldest(entries, bytes_needed)

    return deleted_files


def curate_cache(directory, min_free_percent=5.0, min_free_disk=50):
    """Clear out the directory if needed.

    The curation will only occur if both the precentage and actual disk space
    is below the limit. This assumes all the files in the directory can be
    deleted as freely.

    Args:
        directory (str): directory path that holds cached files
        min_free_percent (float): percentage (0.0-100.0) of drive to keep free,
                                  default is 5% if not specified.
        min_free_disk (float): minimum allowed disk space in MB, default
                               value is 50 MB if not specified.
    """
    # Simpleminded implementation -- keep a certain percentage of the
    # disk available.
    # TODO: Would be easy to add more options, like whitelisted files, etc.
    deleted_files = []
    space = psutil.disk_usage(directory)

    min_free_disk = mb_to_bytes(min_free_disk)
    percent_free = 100.0 - space.percent
    if percent_free < min_free_percent and space.free < min_free_disk:
        LOG.info('Low diskspace detected, cleaning cache')
        # calculate how many bytes we need to delete
        bytes_needed = (min_free_percent - percent_free) / 100.0 * space.total
        bytes_needed = int(bytes_needed + 1.0)

        # get all entries in the directory w/ stats
        entries = _get_cache_entries(directory)
        # delete as many as needed starting with the oldest
        deleted_files = _delete_oldest(entries, bytes_needed)

    return deleted_files


def get_cache_directory(domain=None):
    """Get a directory for caching data.

    This directory can be used to hold temporary caches of data to
    speed up performance.  This directory will likely be part of a
    small RAM disk and may be cleared at any time.  So code that
    uses these cached files must be able to fallback and regenerate
    the file.

    Args:
        domain (str): The cache domain.  Basically just a subdirectory.

    Returns:
        (str) a path to the directory where you can cache data
    """
    config = mycroft.configuration.Configuration.get()
    directory = config.get("cache_path")
    if not directory:
        # If not defined, use /tmp/mycroft/cache
        directory = get_temp_path('mycroft', 'cache')
    return ensure_directory_exists(directory, domain)


def get_directory_size(directory):
    """Get the size of a directory in bytes.

    Args:
        directory (str): path of the directory

    Returns:
        (int) size in bytes or None if directory does not exist
    """
    path = Path(directory)
    if not path.exists():
        return None
    return sum(f.stat().st_size for f in path.glob('**/*') if f.is_file())


def ensure_directory_exists(directory, domain=None, permissions=0o777):
    """Create a directory and give access rights to all

    Args:
        directory (str): Root directory
        domain (str): Domain. Basically a subdirectory to prevent things like
                      overlapping signal filenames.
        rights (int): Directory permissions (default is 0o777)

    Returns:
        (str) a path to the directory
    """
    if domain:
        directory = os.path.join(directory, domain)

    # Expand and normalize the path
    directory = os.path.normpath(directory)
    directory = os.path.expanduser(directory)

    if not os.path.isdir(directory):
        try:
            save = os.umask(0)
            os.makedirs(directory, permissions)
        except OSError:
            LOG.warning("Failed to create: " + directory)
        finally:
            os.umask(save)

    return directory


def create_file(filename):
    """Create the file filename and create any directories needed

    Args:
        filename: Path to the file to be created
    """
    ensure_directory_exists(os.path.dirname(filename), permissions=0o775)
    with open(filename, 'w') as f:
        f.write('')


def get_temp_path(*args):
    """Generate a valid path in the system temp directory.

    This method accepts one or more strings as arguments. The arguments are
    joined and returned as a complete path inside the systems temp directory.
    Importantly, this will not create any directories or files.

    Example usage: get_temp_path('mycroft', 'audio', 'example.wav')
    Will return the equivalent of: '/tmp/mycroft/audio/example.wav'

    Args:
        path_element (str): directories and/or filename

    Returns:
        (str) a valid path in the systems temp directory
    """
    try:
        path = os.path.join(tempfile.gettempdir(), *args)
    except TypeError:
        raise TypeError("Could not create a temp path, get_temp_path() only "
                        "accepts Strings")
    return path
