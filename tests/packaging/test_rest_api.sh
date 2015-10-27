#!/bin/bash

virtualenv_activate="${1}"
CURL="${2}"
GREP="${3}"
unset PYTHONPATH

source "${virtualenv_activate}"

# Start Girder server
export GIRDER_PORT=31200
python -m girder &> /dev/null &

# Ensure the server started
girder_pid=$!
sleep 1
if ! ps -p $girder_pid &> /dev/null ; then
    echo "Error: Girder could not be started"
    exit 1
fi

version="$(girder-install version)"
echo "Detected api version ${version}"

timeout=0
until [ $timeout -eq 5 ]; do
    json=$("${CURL}" --connect-timeout 5 --max-time 5 --silent http://localhost:${GIRDER_PORT}/api/v1/system/version)
    if [ -n "$json" ] && [[ $json == *shortSHA* ]]; then
        break
    fi
    timeout=$((timeout+1))
    sleep 1
done

if [ -n "$json" ]; then
    echo "Girder responded with ${json}"
    python <<EOF
import json
assert json.loads("""${json}""")['apiVersion'].strip() == """${version}""".strip()
EOF
    status=$?
else
    echo "Error: Girder did not respond"
    status=1
fi

kill -9 %+
exit ${status}
