#!/usr/bin/env bash

sha512sum $CIRCLE_WORKING_DIRECTORY/girder/setup.py \
    $CIRCLE_WORKING_DIRECTORY/girder/requirements-dev.txt \
    $CIRCLE_WORKING_DIRECTORY/girder/pytest_girder/setup.py \
    $CIRCLE_WORKING_DIRECTORY/girder/plugins/*/setup.py \
    $CIRCLE_WORKING_DIRECTORY/girder/clients/python/setup.py
