#!/bin/bash

source /usr/share/virtualenvwrapper/virtualenvwrapper.sh
workon girder
cd /home/cpatrick/Dashboards/girder
pip install -r requirements.txt -r requirements-dev.txt -r plugins/metadata_extractor/requirements.txt
python setup.py install
npm install
/usr/local/bin/ctest -VV -S /home/cpatrick/Dashboards/girder/cmake/aiur_nightly.cmake
/usr/local/bin/ctest -VV -S /home/cpatrick/Dashboards/girder/cmake/aiur_nightly_js_coverage.cmake
