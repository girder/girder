#!/bin/bash
set -e

python .circleci/build_plugins.py plugins --extra girder/web

# Build and publish all Python packages in this repo
readonly PUBLISHED_PYTHON_PACKAGES=(
  .
  plugins/*
  pytest_girder
  clients/python
  worker
)
for directory in "${PUBLISHED_PYTHON_PACKAGES[@]}"; do
    echo ==================== "$directory" ====================
    pushd "$directory"
    rm -fr dist
    echo "====== build $directory"
    python -m build
    echo "====== wheel $directory"
    pip wheel . --no-deps -w dist
    echo "====== twine $directory"
    twine ${1:-check} $( [[ "${1:-check}" == "upload" ]] && printf %s '--verbose' ) $( [[ "${1:-check}" == "upload" ]] && printf %s '--skip-existing' ) dist/*
    echo "====== done $directory"
    popd
done
