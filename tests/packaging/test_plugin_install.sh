#!/bin/bash

virtualenv_activate="${1}"
source_path="${2}"

source "${virtualenv_activate}"

girder-install plugin -s "${source_path}"/girder-plugins-*.tar.gz

exit $?
