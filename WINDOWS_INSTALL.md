# Windows Installation

## Pre-requirements
- Python 3.6
- git
- swig
- ffplay (can be downloaded as part of ffmpeg)
- Microsoft Visual C++ Build Tools

All of them should be on PATH enviroment variable of course.

## Installation
``` cmd
> git clone https://github.com/NoamDev/mycroft-core --branch windows

> cd mycroft-core

> .\win_minimal_setup.bat 
```

This might take a few hours


## Starting Mycroft
Run windows-start.bat by double clicking or in CMD.
It would open 5 services in terminal windows, for Message Bus, Skills, Audio, Speech Client and Text Client.

You can stop mycroft by simply closing all 5 terminal windows.