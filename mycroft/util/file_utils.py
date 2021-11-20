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
import xdg.BaseDirectory
from ovos_utils.file_utils import get_temp_path
import mycroft.configuration
from mycroft.util.log import LOG
# do not delete these imports, here for backwards compat!
from ovos_plugin_manager.utils.tts_cache import curate_cache, mb_to_bytes


def resolve_resource_file(res_name):
    """Convert a resource into an absolute filename.

    Resource names are in the form: 'filename.ext'
    or 'path/filename.ext'

    The system wil look for $XDG_DATA_DIRS/mycroft/res_name first
    (defaults to ~/.local/share/mycroft/res_name), and if not found will
    look at /opt/mycroft/res_name, then finally it will look for res_name
    in the 'mycroft/res' folder of the source code package.

    Example:
        With mycroft running as the user 'bob', if you called
        ``resolve_resource_file('snd/beep.wav')``
        it would return either:
        '$XDG_DATA_DIRS/mycroft/beep.wav',
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

    # Now look for XDG_DATA_DIRS
    for path in xdg.BaseDirectory.load_data_paths(mycroft.configuration.BASE_FOLDER):
        filename = os.path.join(path, res_name)
        if os.path.isfile(filename):
            return filename

    # Now look in the old user location
    filename = os.path.join(os.path.expanduser('~'),
                            f'.{mycroft.configuration.BASE_FOLDER}',
                            res_name)
    if os.path.isfile(filename):
        return filename

    # Next look for /opt/mycroft/res/res_name
    data_dir = config.get('data_dir', xdg.BaseDirectory.save_data_path(mycroft.configuration.BASE_FOLDER))
    res_dir = os.path.join(data_dir, 'res')
    filename = os.path.expanduser(os.path.join(res_dir, res_name))
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
    config = mycroft.configuration.Configuration.get(remote=False)
    directory = config.get("cache_path")
    if not directory:
        if not mycroft.configuration.is_using_xdg():
            # If not defined, use /tmp/mycroft/cache
            directory = get_temp_path(mycroft.configuration.BASE_FOLDER, 'cache')
        else:
            directory = os.path.join(xdg.BaseDirectory.xdg_data_home,
                                     mycroft.configuration.BASE_FOLDER, "cache")
    return ensure_directory_exists(directory, domain)


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
    os.chmod(filename, 0o777)
