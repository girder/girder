#!/bin/bash

virtualenv_activate="${1}"
source_path="${2}"
CURL="${3}"
GREP="${4}"

source "${virtualenv_activate}"

girder-install -f web -s "${source_path}"/girder-web-*.tar.gz

export GIRDER_PORT=50202
python -m girder &> /dev/null &

# Loop until girder is giving answers
TIMEOUT=0
until [ $TIMEOUT -eq 15 ]; do
    json=$("${CURL}" -s http://localhost:${GIRDER_PORT}/api/v1/system/version)
    if [ -n "$json" ]; then
        break
    fi
    TIMEOUT=$((TIMEOUT+1))
    sleep 1
done

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
