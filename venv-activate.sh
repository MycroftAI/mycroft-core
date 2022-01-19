#!/usr/bin/env bash
#
# Copyright 2018 Mycroft AI Inc.
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


# This script places the user in the mycroft-core virtual environment,
# necessary to run unit tests or to interact directly with mycroft-core
# via an interactive Python shell.


# wrap in function to allow local variables, since this file will be source'd
function main() { 
    local quiet=0

    for arg in "$@"
    do
        case $arg in
            "-q"|"--quiet" )
               quiet=1
               ;;

            "-h"|"--help" )
               echo "venv-activate.sh:  Enter the Mycroft virtual environment"
               echo "Usage:"
               echo "   source venv-activate.sh"
               echo "or"
               echo "   . venv-activate.sh"
               echo ""
               echo "Options:"
               echo "   -q | --quiet    Don't show instructions."
               echo "   -h | --help    Show help."
               return 0
               ;;

            *)
               echo "ERROR:  Unrecognized option: $@"
               return 1
               ;;
       esac
    done

    if [[ "$0" == "$BASH_SOURCE" ]] ; then
        # Prevent running in script then exiting immediately
        echo "ERROR: Invoke with 'source venv-activate.sh' or '. venv-activate.sh'"
    else
        local SRC_DIR="$( builtin cd "$( dirname "${BASH_SOURCE}" )" ; pwd -P )"
        source ${SRC_DIR}/.venv/bin/activate
        
        # Provide an easier to find "mycroft-" prefixed command.
        unalias mycroft-venv-activate 2>/dev/null
        alias mycroft-venv-deactivate="deactivate && unalias mycroft-venv-deactivate 2>/dev/null && alias mycroft-venv-activate=\"source '${SRC_DIR}/venv-activate.sh'\""
        if [ $quiet -eq 0 ] ; then
            echo "Entering Mycroft virtual environment.  Run 'mycroft-venv-deactivate' to exit"
        fi
    fi
}

main $@
