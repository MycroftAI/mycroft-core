#!/usr/bin/python
"""This script will watch for an idle mic data and restart mycroft.

This script will watch for an in active mic and restart pulseaudio and
mycroft to recover for lost or reconnedted mic.  This takes a bit of time
to recover so give it a couple of minutes.  This completely restarts
mycroft.

This requires setup of the mycroft user for ssh access as the pi user.
Commands to restart mycroft are given as sudo's as the pi user with ssh:

Example:
    To start mycroft message bus
    literal blocks::

        $ ssh pi@localhost ./restart_mycroft.sh

So mycroft user will need a ssh key generated and copied to authorized_keys.
This will allow the mycroft user to ssh without password.  The following
commands can be used set this up.
    literal blocks::

        $ ssh-keygen
        $ ssh-copy-id pi@localhost

Note these commands should be ran as the mycroft user.  The keygen command
can be used just with defaults.  If you include a passcode then it will
be required and cause the script not to work.  The second command the copy
will copy your public key into the authorized_keys. This will require the
password for pi before copying.  You then follow the instruction to from
the command to check if it worked.  You should be fine.

The process is as follows
    1. Check For Changes in mic_level file
    2. Once the changes stop for 20 sec
        A. Kill and Restart pulseaudio
        B. Kill ans restart mycroft
        C. Check the mic file is changing up to 1 min.
    3. Return to step one.

"""
import os.path
import subprocess
import time
import mycroft.util

forever = True

mic_level_file = os.path.join(mycroft.util.get_ipc_directory(), "mic_level")
"""string: location of the mic level file"""

pid_files = ['service','skills','voice']
#start_mycroft = []

#Expand the the pid_files to the full path of the pid files
for i, filex in enumerate(pid_files):
    pid_files[i] = os.path.join(mycroft.util.get_ipc_directory(), "../"+filex+".pid")
    #start_mycroft.append(["./start.sh",filex])


#start_mycroft = [["./mycroft.sh","start","-v"]]

#start_mycroft = []

#for startx in start_mycroft:
#    subprocess.call(startx)

oldData = ""

time_idle = 0

if os.path.isfile(mic_level_file):
    oldData = open(mic_level_file).read()
    indata = oldData
    #Note: The following code may be needed as an alternate workflow.
    #while(indata==oldData):
    #    time.sleep(1)
    #    print "Waiting for File Changes"
    #    indata = open(mic_level_file).read()
    #setup for no change of mic file

while forever:
    if os.path.isfile(mic_level_file):
        time.sleep(1)
        indata = open(mic_level_file).read()
        if (indata == oldData):
            print("File Not changed")
            time_idle = time_idle + 1
            if (time_idle > 20):
                #restart pulseaudio and set source to 0
                subprocess.call(["pulseaudio","-k"])
                subprocess.call(["pulseaudio","-D"])
                subprocess.call(["pacmd","set-default-source","0"])
                #kill mycroft using pid files.
                for filen in pid_files:
                    pid = int(open(filen).read())
                    print "Kill -9",pid
                    subprocess.call(["kill","-9",str(pid)])
                """call mycroft restart script as user pi.

                Note: This is a redundent kill process so should consider
                    removing the kill above and just use the script.
                """
                subprocess.call(["ssh","pi@localhost","./restart_mycroft.sh"])
                #Note: the following lines of code used to start services after kill
                #     Using the script restart_mycroft.sh instead.
                #subprocess.call(["ssh","pi@localhost","sudo","systemctl","start","mycroft-messagebus"])
                #subprocess.call(["ssh","pi@localhost","sudo","systemctl","start","mycroft-skills"])
                #subprocess.call(["ssh","pi@localhost","sudo","systemctl","start","mycroft-speech-client"])
                #for startx in start_mycroft:
                #    subprocess.call(startx)
                time_idle = 0
                #Watch for mic file changes again and abort after a min
                while((indata==oldData)and(time_idle<3)):
                    time.sleep(20)
                    time_idle = time_idle + 1
                    print "Waiting for File Changes"
                    indata = open(mic_level_file).read()
                time_idle = 0
        else:
            oldData = indata
            time_idle = 0
            print("File Changed")

def on_term():
    #consider used for handeling termination but seems to work without.
    #Might want to use this later to terminate by handling kill.
    forever = False
