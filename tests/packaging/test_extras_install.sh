#!/bin/bash

virtualenv_pip="${1}"
PROJECT_SOURCE_DIR="${2}"
virtualenv_activate="${3}"
virtualenv_dir="${4}"
unset PYTHONPATH

# This test attempts to install the girder extra "plugins" which should
# contain celery jobs.  We attempt to import celery as a quick test to
# validate that the extra's option works.

"${virtualenv_pip}" uninstall -y -q celery 2> /dev/null
"${virtualenv_pip}" install "${PROJECT_SOURCE_DIR}[plugins]"
if [ $? -ne 0 ]; then
    echo "Error during pip install girder package with plugins option"
    exit 1
fi

source "${virtualenv_activate}"
which celery
if [ $? -ne 0 ]; then
    echo "Error: celery not found in virtualenv."
    exit 1
fi

exit 0
