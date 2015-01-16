#!/bin/bash

virtualenv_activate="${1}"
source_path="${2}"
unset PYTHONPATH

source "${virtualenv_activate}"

girder-install -f plugin -s "${source_path}"/girder-plugins-*.tar.gz

exit $?
