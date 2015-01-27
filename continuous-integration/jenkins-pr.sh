#!/bin/bash

# Install Python deps
sudo pip install -r \
    requirements.txt -r \
    requirements-dev.txt -r \
    plugins/geospatial/requirements.txt -r \
    plugins/metadata_extractor/requirements.txt -r \
    plugins/celery_jobs/requirements.txt

# We have to upgrade six or requiring moto can cause other modules to fail
sudo pip install -U six

# We have to import bcrypt to trigger a build of that
sudo python -c "import bcrypt"

# Install Javascript deps
npm install

# Now Build
mkdir _build
cd _build
cmake ..
ctest -VV -S ../cmake/travis_continuous.cmake || true
if [ -f test_failed ] ; then false ; fi
