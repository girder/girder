#!/bin/bash

export PYTHON_VERSION=`pyenv version-name`
export COVERAGE_EXECUTABLE=`pyenv which coverage`
export FLAKE8_EXECUTABLE=`pyenv which flake8`
export VIRTUALENV_EXECUTABLE=`pyenv which virtualenv`
export PYTHON_EXECUTABLE=`pyenv which python`

case $CIRCLE_NODE_INDEX in
    0|1)
        export TEST_GROUP=python
        ;;
    2)
        export TEST_GROUP=browser
        ;;
    *)
        echo "Invalid node index"
        exit 0
esac

mkdir $HOME/build

ctest -R '^py_coverage_reset$' -VV -S $HOME/girder/cmake/circle_continuous.cmake

if [ "$TEST_GROUP" == "python" ]; then
    if ! pytest --mock-db --tb=long --junit-xml=$CIRCLE_TEST_REPORTS/pytest-${CIRCLE_NODE_INDEX}.xml; then
        touch $HOME/build/test_failed
    fi
fi

# pytest also generates coverage, so don't reset coverage at the start of the run
ctest -E '^(py_coverage_reset|server_pytest_core)$' -VV -S $HOME/girder/cmake/circle_continuous.cmake

# Convert CTest output to Junit and ensure CircleCI will include it in its summary
pip install scikit-ci-addons==0.15.0
mkdir ${CIRCLE_TEST_REPORTS}/CTest
ci_addons ctest_junit_formatter $HOME/build > ${CIRCLE_TEST_REPORTS}/CTest/JUnit-${CIRCLE_NODE_INDEX}.xml || exit 1
if [ -f $HOME/build/test_failed ] ; then
    exit 1
fi

mkdir -p $CIRCLE_ARTIFACTS/coverage/python $CIRCLE_ARTIFACTS/coverage/js
cp -r ~/build/coverage.xml ~/girder/clients/web/dev/built/py_coverage/* $CIRCLE_ARTIFACTS/coverage/python
cp -r ~/build/coverage/* $CIRCLE_ARTIFACTS/coverage/js
bash <(curl -s https://codecov.io/bash) || echo "Codecov did not collect coverage reports"
