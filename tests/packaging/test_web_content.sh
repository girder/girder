#!/bin/bash

virtualenv_activate="${1}"
source_path="${2}"
CURL="${3}"
GREP="${4}"

source "${virtualenv_activate}"

girder-install -f web -s "${source_path}"/girder-web-*.tar.gz

export GIRDER_PORT=50012
python -m girder &> /dev/null &

sleep 5

"${CURL}" -s http://localhost:${GIRDER_PORT} | "${GREP}" "g-global-info-apiroot" > /dev/null
if [ $? -ne 0 ] ; then
    echo "Failed to load main page"
    exit $?
fi

"${CURL}" -s http://localhost:${GIRDER_PORT}/api/v1 | "${GREP}" "swagger" > /dev/null
if [ $? -ne 0 ] ; then
    echo "Failed to load swagger docs"
    exit $?
fi

kill -9 %+

exit 0
