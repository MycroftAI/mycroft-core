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
from signal import getsignal, signal, SIGKILL, SIGINT, SIGTERM, \
    SIG_DFL, default_int_handler, SIG_IGN  # signals
from mycroft.configuration import BASE_FOLDER
import os  # Operating System functions

#
# Wrapper around chain of handler functions for a specific system level signal.
# Often used to trap Ctrl-C for specific application purposes.
from mycroft.util import LOG
from mycroft.util.file_utils import get_temp_path


class Signal:  # python 3+ class Signal

    """
    Capture and replace a signal handler with a user supplied function.
    The user supplied function is always called first then the previous
    handler, if it exists, will be called.  It is possible to chain several
    signal handlers together by creating multiply instances of objects of
    this class, providing a  different user functions for each instance.  All
    provided user functions will be called in LIFO order.
    """

    #
    # Constructor
    # Get the previous handler function then set the passed function
    # as the new handler function for this signal

    def __init__(self, sig_value, func):
        """
        Create an instance of the signal handler class.

        sig_value:  The ID value of the signal to be captured.
        func:  User supplied function that will act as the new signal handler.
        """
        super(Signal, self).__init__()  # python 3+ 'super().__init__()
        self.__sig_value = sig_value
        self.__user_func = func  # store user passed function
        self.__previous_func = signal(sig_value, self)
        self.__previous_func = {  # Convert signal codes to functions
            SIG_DFL: default_int_handler,
            SIG_IGN: lambda a, b: None
        }.get(self.__previous_func, self.__previous_func)

    #
    # Called to handle the passed signal
    def __call__(self, signame, sf):
        """
        Allows the instance of this class to be called as a function.
        When called it runs the user supplied signal handler than
        checks to see if there is a previously defined handler.  If
        there is a previously defined handler call it.
        """
        self.__user_func()
        self.__previous_func(signame, sf)

    #
    # reset the signal handler
    def __del__(self):
        """
        Class destructor.  Called during garbage collection.
        Resets the signal handler to the previous function.
        """
        signal(self.__sig_value, self.__previous_func)

    # End class Signal


# ----------------------------------------------------------------------------
# ----------------------------------------------------------------------------


#
# Create, delete and manipulate a PID file for this service
# ------------------------------------------------------------------------------
class Lock:  # python 3+ 'class Lock'

    """
    Create and maintains the PID lock file for this application process.
    The PID lock file is located in /tmp/mycroft/*.pid.  If another process
    of the same type is started, this class will 'attempt' to stop the
    previously running process and then change the process ID in the lock file.
    """

    #
    # Class constants
    DIRECTORY = get_temp_path(BASE_FOLDER)
    FILE = '/{}.pid'

    #
    # Constructor
    def __init__(self, service):
        """
        Builds the instance of this object.  Holds the lock until the
        object is garbage collected.

        service: Text string.  The name of the service application
        to be locked (ie: skills, voice)
        """
        super(Lock, self).__init__()  # python 3+ 'super().__init__()'
        self.__pid = os.getpid()  # PID of this application
        self.path = Lock.DIRECTORY + Lock.FILE.format(service)
        self.set_handlers()  # set signal handlers
        self.create()

    #
    # Reset the signal handlers to the 'delete' function
    def set_handlers(self):
        """
        Trap both SIGINT and SIGTERM to gracefully clean up PID files
        """
        self.__handlers = {SIGINT: Signal(SIGINT, self.delete),
                           SIGTERM: Signal(SIGTERM, self.delete)}

    #
    # Check to see if the PID already exists
    #  If it does exits perform several things:
    #    Stop the current process
    #    Delete the exiting file
    def exists(self):
        """
        Check if the PID lock file exists.  If it does
        then send a SIGKILL signal to the process defined by the value
        in the lock file.  Catch the keyboard interrupt exception to
        prevent propagation if stopped by use of Ctrl-C.
        """
        if not os.path.isfile(self.path):
            return
        with open(self.path, 'r') as L:
            try:
                os.kill(int(L.read()), SIGKILL)
            except Exception as E:
                pass

    #
    # Create a lock file for this server process
    def touch(self):
        """
        If needed, create the '/tmp/mycroft' directory than open the
        lock file for writting and store the current process ID (PID)
        as text.
        """
        if not os.path.exists(Lock.DIRECTORY):
            os.makedirs(Lock.DIRECTORY)
        with open(self.path, 'w') as L:
            L.write('{}'.format(self.__pid))

    #
    # Create the PID file
    def create(self):
        """
        Checks to see if a lock file for this service already exists,
        if so have it killed.  In either case write the process ID of
        the current service process to to the existing or newly created
        lock file in /tmp/mycroft/
        """
        self.exists()  # check for current running process
        self.touch()

    #
    # Delete the PID file - but only if it has not been overwritten
    # by a duplicate service application
    def delete(self, *args):
        """
        If the PID lock file contains the PID of this process delete it.

        *args: Ignored.  Required as this fuction is called as a signel
        handler.
        """
        try:
            with open(self.path, 'r') as L:
                pid = int(L.read())
                if self.__pid == pid:
                    os.unlink(self.path)
        except IOError:
            pass
    # End class Lock
