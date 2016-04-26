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

import dicom

from girder.constants import AccessType
from girder.utility.model_importer import ModelImporter

from utils.dicom_json_conversion import datasetToJSON


def addDICOMMetadata(file, path):
    """
    Read DICOM file at path and add data elements as metadata to the file's
    item.

    :param file: file object
    :type file: file
    :param path: path of the DICOM file
    :type path: str
    """
    try:
        dcm = dicom.read_file(path)
    except dicom.filereader.InvalidDicomError:
        # XXX: some DICOM files omit the 'DICM' header; force=True is required
        return False

    itemModel = ModelImporter.model('item')
    userModel = ModelImporter.model('user')

    user = userModel.load(file['creatorId'], level=AccessType.READ)
    item = itemModel.load(file['itemId'], level=AccessType.WRITE, user=user)

    metadata = datasetToJSON(dcm)

    updatedItem = itemModel.setMetadata(item, metadata)
    itemModel.updateItem(updatedItem)

    return True
