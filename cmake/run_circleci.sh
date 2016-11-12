#!/bin/bash

export PYTHON_VERSION=`pyenv version-name`
export COVERAGE_EXECUTABLE=`pyenv which coverage`
export FLAKE8_EXECUTABLE=`pyenv which flake8`
export VIRTUALENV_EXECUTABLE=`pyenv which virtualenv`
export PYTHON_EXECUTABLE=`pyenv which python`

touch $HOME/_build/test_failed
ctest -VV -S $HOME/girder/cmake/circle_continuous.cmake
if [ -f $HOME/_build/test_failed ] ; then
	exit 1
fi
