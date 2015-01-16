#!/bin/bash

virtualenv_pip="${1}"
PROJECT_SOURCE_DIR="${2}"
unset PYTHONPATH

"${virtualenv_pip}" uninstall girder > /dev/null
"${virtualenv_pip}" install -U "${PROJECT_SOURCE_DIR}"/girder-[0-9].[0-9]*.tar.gz > /dev/null
exit $?
