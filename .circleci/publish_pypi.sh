#!/bin/bash
set -e

python .circleci/build_plugins.py plugins/

# Build and publish sdist's for all Python packages in this repo
readonly PUBLISHED_PYTHON_PACKAGES=(
  .
  plugins/*
  pytest_girder
  clients/python
)
for directory in "${PUBLISHED_PYTHON_PACKAGES[@]}"; do
    pushd "$directory"
    rm -fr dist
    python setup.py sdist
    popd
    twine upload --skip-existing "$directory/dist/*"
done
