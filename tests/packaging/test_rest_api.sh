#!/bin/bash

virtualenv_activate="${1}"
CURL="${2}"
GREP="${3}"
unset PYTHONPATH

source "${virtualenv_activate}"

export GIRDER_PORT=31200
python -m girder &> /dev/null &

version="$(girder-install version)"
echo "Detected api version ${version}"

TIMEOUT=0
until [ $TIMEOUT -eq 15 ]; do
    json=$("${CURL}" -s http://localhost:${GIRDER_PORT}/api/v1/system/version)
    if [ -n "$json" ] && [[ $json == *shortSHA* ]]; then
        break
    fi
    TIMEOUT=$((TIMEOUT+1))
    sleep 1
done

echo "Girder responded with ${json}"

python <<EOF
import json
assert json.loads("""${json}""")['apiVersion'].strip() == """${version}""".strip()
EOF

status=$?

kill -9 %+

exit ${status}
