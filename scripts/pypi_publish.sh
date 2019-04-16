#!/bin/bash
set -e

# build sdist's for all python packages in this repo
for d in . plugins/* pytest_girder clients/python ; do
    pushd $d
    rm -fr dist
    python setup.py sdist
    popd
done
twine upload --skip-existing dist/* plugins/*/dist/* clients/python/dist/* pytest_girder/dist/*
