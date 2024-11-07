#!/bin/bash

PIP=${PIP_BIN:-pip}
PYTHON=${PYTHON_BIN:-python}

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


# Hack to make sure docker.sock has a real group, and that the
# 'worker' user is apart of that group.
if [ -e /var/run/docker.sock ]; then
    if [ $(stat -c %G /var/run/docker.sock) == 'UNKNOWN' ]; then
        groupadd -g $(stat -c %g /var/run/docker.sock) dockermock
        usermod -aG dockermock worker
    else
        usermod -aG $(stat -c %G /var/run/docker.sock) worker
    fi
fi

mkdir tmp
chmod 777 tmp

# TODO: convert this to run celery -A girder_worker.app worker -l info once
# python2 integration tests are removed.
sudo --preserve-env -u worker $PYTHON -m girder_worker -l info
