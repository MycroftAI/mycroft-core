#!/bin/bash
# Script to setup the integration test environment and run the tests.
#
# The comands runing in this script are those that need to be executed at
# runtime. Assumes running within a Docker container where the PATH environment
# variable has been set to include the virtual envionrment's bin directory

# Start all mycroft core services.
pwd
/opt/mycroft/mycroft-core/start-mycroft.sh all
# Run the integration test suite.  Results will be formatted for input into
# the Allure reporting tool.
behave -f allure_behave.formatter:AllureFormatter -o allure-results
RESULT=$?
# Stop all mycroft core services.
/opt/mycroft/mycroft-core/stop-mycroft.sh all

# Remove temporary skill files
rm -rf ~/.mycroft/skills
# Remove intent cache
rm -rf ~/.mycroft/intent_cache

exit $RESULT
