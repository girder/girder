#!/bin/bash
set -e

# Build sdist's for all Python packages in this repo, then check them, or
# with "upload", publish them
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
    if [[ "$1" == "upload" ]]; then
        twine upload --skip-existing "$directory/dist/*"
    else
        twine check "$directory/dist/*"
    fi
done
