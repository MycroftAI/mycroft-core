#!/bin/bash
# Script to setup the integration test environment and run the tests.
#
# The comands runing in this script are those that need to be executed at
# runtime. Assumes running within a Docker container where the PATH environment
# variable has been set to include the virtual envionrment's bin directory

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

# Start pulseaudio if running in CI environment
if [[ -v CI ]]; then
    # Ensure pulseaudio is stateless on start up
    # This stops the daemon from randomly failing on startup
    # See https://superuser.com/a/1545361 for more info
    rm -rf /root/.config/pulse
    pulseaudio -D
fi
# Start all mycroft core services.
${SCRIPT_DIR}/../../../start-mycroft.sh all
# Run the integration test suite.  Results will be formatted for input into
# the Allure reporting tool.
echo "Running behave with the arguments \"$@\""
behave $@
RESULT=$?
if [[ -v CI ]]; then
    # Stop all mycroft core services if running in CI environment.
    ${SCRIPT_DIR}/../../../stop-mycroft.sh all
fi

# Reort the result of the behave test as exit status
exit $RESULT
