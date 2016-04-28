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

import six

import dicom
from dicom.dataelem import DataElement

from girder.constants import AccessType
from girder.utility.model_importer import ModelImporter

from .dicom_json_conversion import dataElementToJSON, datasetToJSON


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

    userModel = ModelImporter.model('user')
    itemModel = ModelImporter.model('item')

    query = {
        'meta.0020000D.Value': dcm.StudyInstanceUID
    }
    fields = {
        'meta.0020000E.Value': True,
        'meta.00080060.Value': True
    }
    cursor = itemModel.find(query, fields=fields)

    # Gather metadata on existing items
    numSeries = len(cursor.distinct('meta.0020000E.Value'))
    numInstances = cursor.count()
    modalitiesInStudy = cursor.distinct('meta.00080060.Value')

    # Update metadata for new item
    numSeries = max(numSeries, 1)
    numInstances += 1
    if modalitiesInStudy is None:
        modalitiesInStudy = [dcm.Modality]
    elif dcm.Modality not in modalitiesInStudy:
        modalitiesInStudy.append(dcm.Modality)
    modalitiesInStudy.sort()

    user = userModel.load(file['creatorId'], level=AccessType.READ)
    item = itemModel.load(file['itemId'], level=AccessType.WRITE, user=user)

    metadata = datasetToJSON(dcm)

    updatedItem = itemModel.setMetadata(item, metadata)
    itemModel.updateItem(updatedItem)

    # Update derived attributes on all items in study
    data = {}
    data.update(dataElementToJSON(
        DataElement((0x0020, 0x1206), 'IS', str(numSeries))))
    data.update(dataElementToJSON(
        DataElement((0x0020, 0x1208), 'IS', str(numInstances))))
    data.update(dataElementToJSON(
        DataElement((0x0008, 0x0061), 'CS', '\\'.join(modalitiesInStudy))))

    updateData = {}
    for key, value in six.viewitems(data):
        updateData['meta.' + key] = value

    query = {
        'meta.0020000D.Value': dcm.StudyInstanceUID
    }
    update = {
        '$set': updateData
    }
    itemModel.update(query, update, multi=True)

    return True
