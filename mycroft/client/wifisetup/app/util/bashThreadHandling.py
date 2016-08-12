import threading
import subprocess
import sys

class cmd_thread(threading.Thread):
    def __init__(self, cmd):#, timeout):
        threading.Thread.__init__(self)
        self.cmd = cmd
        #self.timeout = timeout
        self._return ="No Output"
    def run(self):
        try:
            proc = subprocess.Popen(self.cmd,
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE)
            stdout, stderr = proc.communicate()
            if stdout:
                self._return = {'exit':0, 'returncode':proc.returncode,'stdout':stdout}
            if stderr:
                self._return = {'exit':0, 'returncode':proc.returncode, 'stdout':stderr}
        except OSError as e:
            self._return = {'exit':1, 'os_errno':e.errno, 'os_stderr':e.strerror, 'os_filename':e.filename}
        except:
            self._return = {'exit':2, 'sys':sys.exc_info()[0]}

    def join(self):
        threading.Thread.join(self) #, timeout=self.timeout)
        return self._return

def bash_command(command):
    proc = cmd_thread(command) #, 10)
    #proc.setDaemon(True)
    proc.start()
    return proc.join()

def bash_command_daemon(command):
    proc = cmd_thread(command)
    proc.start()