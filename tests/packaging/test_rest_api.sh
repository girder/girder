#!/bin/bash

virtualenv_activate="${1}"
CURL="${2}"
GREP="${3}"

source "${virtualenv_activate}"

export GIRDER_PORT=50011
python -m girder &> /dev/null &

sleep 5

version="$(girder-install version)"
echo "Detected api version ${version}"

json=$("${CURL}" -s http://localhost:${GIRDER_PORT}/api/v1/system/version)
echo "Girder responded with ${json}"

python <<EOF
import json
assert json.loads("""${json}""")['apiVersion'].strip() == """${version}""".strip()
EOF

status=$?

kill -9 %+

exit ${status}
