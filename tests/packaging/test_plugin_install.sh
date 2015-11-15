#!/bin/bash

virtualenv_activate="${1}"
source_path="${2}"
unset PYTHONPATH

source "${virtualenv_activate}"

girder-install plugin "${source_path}/plugins/thumbnails"

if [ $? -eq 0 ] ; then
    echo "Error: expected an error when installing an existing plugin without -f"
    exit 1
fi

girder-install plugin -f "${source_path}/plugins/thumbnails"

exit $?
