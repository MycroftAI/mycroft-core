Mycroft [![Build Status](https://travis-ci.org/MycroftAI/mycroft-core.svg?branch=master)](https://travis-ci.org/MycroftAI/mycroft-core) [![Coverage Status](https://coveralls.io/repos/github/MycroftAI/mycroft-core/badge.svg?branch=dev)](https://coveralls.io/github/MycroftAI/mycroft-core?branch=dev)
==========

NOTE: The default branch for this repository is 'dev', which should be considered a working beta. If you want to clone a more stable version, switch over to the 'master' branch.  

Documentation: https://docs.mycroft.ai

Release Notes: https://docs.mycroft.ai/release-notes

Pair Mycroft Device: https://home.mycroft.ai

Mycroft Chat Network: https://mycroft.ai/to/chat

Looking to join in developing?  Check out the [Project Wiki](../../wiki/Home) for tasks you can tackle!

# Getting Started

- Run `install.sh` (It will install OS dependencies and prepare the python virtualenv).

- [Running Mycroft Quick Start](#running-mycroft-quick-start)

### Other Environments
The following packages are required for setting up the development environment and are installed by `./scripts/distro/install_<DISTRO>.sh` scripts:

 - `git`
 - `python 2`
 - `python-setuptools`
 - `python-virtualenv`
 - `pygobject`
 - `virtualenvwrapper`
 - `libtool`
 - `libffi`
 - `openssl`
 - `autoconf`
 - `bison`
 - `swig`
 - `glib2.0`
 - `s3cmd`
 - `portaudio19`
 - `mpg123`
 - `flac`
 - `curl`

## Home Device and Account Manager
Mycroft AI, Inc. maintains a device and account management system known as Mycroft Home. Developers may sign up at: https://home.mycroft.ai

By default, Mycroft software is configured to use Home. Upon any request such as "Hey Mycroft, what is the weather?", you will be informed that your device needs to be paired. Mycroft will speak a 6-digit code, which is entered into the pairing page within the [Mycroft Home site](https://home.mycroft.ai).

Once signed and paired, your unit will use Mycroft API keys for services such as STT (Speech-to-Text), weather, Wolfram-Alpha, and various other skills.

Pairing information generated by registering with Home is stored in:

`~/.mycroft/identity/identity2.json` <b><-- DO NOT SHARE THIS WITH OTHERS!</b>

It is useful to know the location of this identity file when troubleshooting any device pairing issues.

## Using Mycroft Without Home.
If you do not wish to use the Mycroft Home service, you may insert your own API keys into the configuration files listed below in <b>configuration</b>.

The place to insert the API key looks like the following:

`[WeatherSkill]`

`api_key = ""`

Put a relevant key inside the quotes and Mycroft Core should begin to use the key immediately.

### API Key Services
These are the keys currently used in Mycroft Core:

- [STT API, Google STT](http://www.chromium.org/developers/how-tos/api-keys)
- [Weather Skill API, OpenWeatherMap](http://openweathermap.org/api)
- [Wolfram-Alpha Skill](http://products.wolframalpha.com/api/)

## Configuration
Mycroft configuration consists of 4 possible locations:
- `mycroft-core/mycroft/configuration/mycroft.conf`(Defaults)
- [Mycroft Home](https://home.mycroft.ai) (Remote)
- `/etc/mycroft/mycroft.conf`(Machine)
- `$HOME/.mycroft/mycroft.conf`(User)

When the configuration loader starts, it looks in these locations in this order, and loads ALL configurations. Keys that exist in multiple configuration files will be overridden by the last file to contain the value. This process results in a minimal amount being written for a specific device and user, without modifying default distribution files.

# Running Mycroft Quick Start
To start essential tasks, run `./mycroft.sh start`. This command will start the Mycroft service, skills, voice, and command line interface (cli) using `--quiet mode` in a detached screen.  Output of these screens will be written to their respective log files (e.g. ./log/mycroft-service.log).

Optionally, you may run `./mycroft.sh start -v` which will start the Mycroft service, skills, and voice. 

You may also run `./mycroft.sh start -c` which will start the Mycroft service, skills and command line interface.

To stop Mycroft, run `./mycroft.sh stop`. This command will terminate all detached screens.

To restart Mycroft, run `./mycroft.sh restart`.

# Quick Screen Tips
- Run `screen -list` to see all running screens.

- Run `screen -r [screen-name]` (e.g. `screen -r mycroft-service`) to reattach a screen.

- To detach a running screen, press `Ctrl + a, Ctrl + d`

See the [screen man page](http://man7.org/linux/man-pages/man1/screen.1.html) for more details.

# Running Mycroft
## With `start.sh`
Mycroft provides `start.sh` to run a large number of common tasks. This script uses a virtualenv created by `dev_setup.sh`. The usage statement lists all run targets, but to run a Mycroft stack out of a git checkout, the following processes should be started:

- Run `./start.sh service`
- Run `./start.sh skills`
- Run `./start.sh voice`

*Note: The above scripts are blocking, so each will need to be run in a separate terminal session.*

## Without `start.sh`
Activate your virtualenv.

With virtualenv-wrapper:
```
workon mycroft
```

Without virtualenv-wrapper:
```
source ~/.virtualenvs/mycroft/bin/activate
```

- Run `PYTHONPATH=. python client/speech/main.py` # Main speech detection loop, which prints events to stdout and broadcasts them to the message bus.
- Run `PYTHONPATH=. python client/messagebus/service/main.py` # Main message bus, implemented via web sockets.
- Run `PYTHONPATH=. python client/skills/main.py` # Main skills executable, loads all skills under skills directory.

*Note: The above scripts are blocking, so each will need to be run in a separate terminal session. Each terminal session will require that the virtualenv be activated. There are very few reasons to use this method.*

# FAQ / Common Errors

#### When running Mycroft, I get the error `mycroft.messagebus.client.ws - ERROR - Exception("Uncaught 'error' event.",)`

This means that you are not running the `./start.sh service` process. In order to fully run Mycroft, you must run `./start.sh service`, `./start.sh skills`, `./start.sh voice`, and `./start.sh cli` all at the same time. This can be done using different terminal windows, or by using the included `./mycroft.sh start` command, which runs all four process using `screen`.
