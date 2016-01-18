#!/bin/bash

virtualenv_pip="${1}"
PROJECT_SOURCE_DIR="${2}"
virtualenv_activate="${3}"
virtualenv_dir="${4}"
unset PYTHONPATH

"${virtualenv_pip}" uninstall -y girder > /dev/null
"${virtualenv_pip}" --no-cache-dir install -U "${PROJECT_SOURCE_DIR}"/girder-[0-9].[0-9]*.tar.gz
if [ $? -ne 0 ]; then
    echo "Error during pip install girder package"
    exit 1
fi

source "${virtualenv_activate}"
which girder-server
if [ $? -ne 0 ]; then
    echo "Error: girder-server not found on the executable path"
    exit 1
fi

ls "${virtualenv_dir}"/lib/python*/site-packages/girder/mail_templates/_header.mako
if [ $? -ne 0 ]; then
    echo "Error: mail templates were not installed"
    exit 1
fi

exit 0
