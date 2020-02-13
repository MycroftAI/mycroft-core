#!/bin/bash
# Script to setup the integration test environment and run the tests.
#
# The comands runing in this script are those that need to be executed at
# runtime. Assumes running within a Docker container where the PATH environment
# variable has been set to include the virtual envionrment's bin directory

# Start all mycroft core services.
/opt/mycroft/mycroft-core/start-mycroft.sh all
# Run the integration test suite.  Results will be formatted for input into
# the Allure reporting tool.
behave -f allure_behave.formatter:AllureFormatter -o ~/.mycroft/allure-result
RESULT=$?
# Stop all mycroft core services.
/opt/mycroft/mycroft-core/stop-mycroft.sh all
# Make the jenkins user the owner of the allure results.  This allows the
# jenkins job to build a report from the results
chown --recursive 110:116 ~/.mycroft/allure-result
# Remove temporary skill files
rm -rf ~/.mycroft/skills
# Remove intent cache
rm -rf ~/.mycroft/intent_cache

exit $RESULT
