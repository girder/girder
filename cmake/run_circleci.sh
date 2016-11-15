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
		exit 1
esac

mkdir $HOME/build
touch $HOME/build/test_failed
ctest -VV -S $HOME/girder/cmake/circle_continuous.cmake
if [ -f $HOME/build/test_failed ] ; then
	exit 1
fi

mkdir -p $CIRCLE_ARTIFACTS/coverage/python $CIRCLE_ARTIFACTS/coverage/js
cp -r ~/build/coverage.xml ~/girder/clients/web/dev/built/py_coverage/* $CIRCLE_ARTIFACTS/coverage/python
cp -r ~/build/coverage/* $CIRCLE_ARTIFACTS/coverage/js
bash <(curl -s https://codecov.io/bash) || echo "Codecov did not collect coverage reports"
