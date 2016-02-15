#!/bin/bash

# Main driver script for garant nightly testing.  The primary purpose
# of this nightly dashboard is to test girder against the most recent
# packages on PyPI.  Other dashboards and CI tests only test girder
# against a specific frozen python environment.  This dashboard is
# expected to fail from time to time and exists to catch bugs due to
# upstream changes before users encounter them.

# This script is run by cron in the following entry:
#
#   0 2 * * * $HOME/Dashboards/girder/cmake/run_garant_dashboard.sh >> /tmp/girder-nightly.log 2>&1

. $HOME/.bash_profile

# Build prefix
b=$HOME/Builds

# Source prefix
d=$HOME/Dashboards

# girder source path
g=$d/girder

# girder branch to test
branch=master

# ctest binary path
ctest=/opt/cmake-3.4.1-Linux-x86_64/bin/ctest

function runtest {
  echo "**************** $1 start ****************"
  date
  echo ""
  pyenv shell $1
  pyenv rehash
  pip install -U virtualenv pip
  rm -fr "$b/girder-${PYENV_VERSION}"
  mkdir -p "$b/girder-${PYENV_VERSION}"
  virtualenv "$b/girder-${PYENV_VERSION}/test-venv"
  source "$b/girder-${PYENV_VERSION}/test-venv/bin/activate"

  # Create a virtualenv for packaging.  For some reason, trying to install
  # the virtualenv fails on garant during the build.  Instead, we just create
  # it manually here.
  virtualenv "$b/girder-${PYENV_VERSION}/env"

  export PYTHON_EXECUTABLE="$(pyenv which python)"
  export VIRTUALENV_EXECUTABLE="$(pyenv which virtualenv)"
  export PIP_EXECUTABLE="$(pyenv which pip)"
  export NPM_EXECUTABLE="$(which npm)"
  export GIRDER_PATH="$g"
  export GIRDER_BRANCH="$branch"
  export PYENV_VERSION
  "$ctest" -S "$g/cmake/garant_nightly.cmake" -VV
  deactivate
  echo "**************** $1 done *****************"
  echo ""
}

runtest "2.7.10"
runtest "3.4.3"
