#!/bin/bash

PIP=${PIP_BIN:-pip}
BIN=${PYTHON_BIN:-python}

# If /girder_worker/setup.py exists then we've
# mounted girder_worker at run time,  make sure it
# is properly installed before continuing
if [ -e /girder_worker/setup.py ]; then
    $PIP uninstall -y girder-worker
    $PIP install -e /girder_worker
fi

# If common_tasks/setup.py exists then we've
# mounted girder_worker at run time,  make sure it
# is properly installed before continuing
if [ -e /girder_worker/tests/integration/common_tasks/setup.py ]; then
    $PIP uninstall -y common-tasks
    $PIP install -e /girder_worker/tests/integration/common_tasks/
fi

# If integration_test_endpoints/setup.py exists then we've
# mounted girder_worker at run time,  make sure it
# is properly installed before continuing
if [ -e /girder_worker/tests/integration/common_tasks/setup.py ]; then
    $PIP uninstall -y integration_test_endpoints
    $PIP install -e /girder_worker/tests/integration/integration_test_endpoints/
fi

girder serve "$@"
