#!/usr/bin/env python
# -*- coding: utf-8 -*-

###############################################################################
#  Copyright Kitware Inc.
#
#  Licensed under the Apache License, Version 2.0 ( the "License" );
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
###############################################################################

import os

from girder import events
from girder.constants import AssetstoreType

from .metadata import addDICOMMetadata
from .rest import studies, series, instances


def dicom_handler(event):
    # \todo Add support for other assetstore
    # \todo Make something actually useful with the metadata

    assetstore = event.info['assetstore']
    if assetstore['type'] != AssetstoreType.FILESYSTEM:
        return

    file = event.info['file']
    path = os.path.join(assetstore['root'], file['path'])

    addDICOMMetadata(file, path)


def load(info):
    info['apiRoot'].studies = studies.dicomStudies()
    info['apiRoot'].series = series.dicomSeries()
    info['apiRoot'].instances = instances.dicomInstances()

events.bind('data.process', 'dicom_handler', dicom_handler)
