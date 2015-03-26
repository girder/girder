#!/bin/bash

source /usr/share/virtualenvwrapper/virtualenvwrapper.sh
workon girder
cd /home/cpatrick/Dashboards/girder
pip install -r requirements.txt -r requirements-dev.txt -r plugins/metadata_extractor/requirements.txt -r plugins/geospatial/requirements.txt -r plugins/celery_jobs/requirements.txt -r plugins/hdfs_assetstore/requirements.txt
npm install
python setup.py install
# Copy compile plugin template files so that the javascript coverage locates
# them properly.  There are certainly nicer ways to do this.
find /home/cpatrick/Dashboards/girder/clients/web/static/built/plugins/ -name templates.js -exec python -c 'import shutil;path = """{}""";shutil.copy(path, path.replace("/clients/web/static/built/plugins/","/plugins/"))' \;
JASMINE_TIMEOUT=15000 /usr/local/bin/ctest -VV -S /home/cpatrick/Dashboards/girder/cmake/aiur_nightly.cmake
/usr/local/bin/ctest -VV -S /home/cpatrick/Dashboards/girder/cmake/aiur_nightly_js_coverage.cmake
