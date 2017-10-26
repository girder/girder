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
import six
from dicom.sequence import Sequence
from dicom.valuerep import PersonName3

from girder import events
from girder.api import access
from girder.api.describe import Description, autoDescribeRoute
from girder.api.rest import Resource
from girder.constants import AccessType, TokenScope
from girder.models.item import Item
from girder.models.file import File


class DicomItem(Resource):

    @access.user(scope=TokenScope.DATA_READ)
    @autoDescribeRoute(
        Description('Get and store common DICOM metadata, if any, for all files in the item.')
        .modelParam('id', 'The item ID',
                    model='item', level=AccessType.WRITE, paramType='path')
        .errorResponse('ID was invalid.')
        .errorResponse('Read permission denied on the item.', 403)
    )
    def makeDicomItem(self, item):
        """
        Try to convert an existing item into a "DICOM item", which contains a
        "dicomMeta" field with DICOM metadata that is common to all DICOM files.
        """
        metadataReference = None
        dicomFiles = []

        for file in Item().childFiles(item):
            dicomMeta = _parseFile(file)
            if dicomMeta is None:
                continue
            dicomFiles.append(_extractFileData(file, dicomMeta))

            metadataReference = (
                dicomMeta
                if metadataReference is None else
                _removeUniqueMetadata(metadataReference, dicomMeta)
            )

        if dicomFiles:
            # Sort the dicom files
            dicomFiles.sort(key=_getDicomFileSortKey)
            # Store in the item
            item['dicom'] = {
                'meta': metadataReference,
                'files': dicomFiles
            }
            # Save the item
            Item().save(item)


def _extractFileData(file, dicom):
    """
    Extract the usefull data to be stored in the `item['dicom']['files']`.
    In this way it become simpler to sort them and store them.
    """
    return {
        'dicom': {
            'SeriesNumber': dicom.get('SeriesNumber'),
            'InstanceNumber': dicom.get('InstanceNumber'),
            'SliceLocation': dicom.get('SliceLocation')
        },
        'name': file['name'],
        '_id': file['_id']
    }


def _getDicomFileSortKey(f):
    """These properties are used to sort the files into the item."""
    meta = f.get('dicom')
    return (
        meta.get('SeriesNumber'),
        meta.get('InstanceNumber'),
        meta.get('SliceLocation'),
        f.get('name')
    )


def _removeUniqueMetadata(dicomMeta, additionalMeta):
    """
    Return only the common data between the two inputs.
    Only work if all the data element are hashable,
    this means not have any dict or list as properties
    """
    return dict(
        set(
            (
                k,
                tuple(v) if isinstance(v, list) else v
            )
            for k, v in six.viewitems(dicomMeta)
        ) &
        set(
            (
                k,
                tuple(v) if isinstance(v, list) else v
            )
            for k, v in six.viewitems(additionalMeta)
        )
    )


def _coerce(x):
    if isinstance(x, Sequence):
        return None
    if isinstance(x, list):
        return [_coerce(y) for y in x]
    if isinstance(x, PersonName3):
        return x.encode('utf-8')
    try:
        six.text_type(x)
        return x
    except Exception:
        return None


def _parseFile(f):
    data = {}
    try:
        # download file and try to parse dicom
        with File().open(f) as fp:
            ds = dicom.read_file(
                fp,
                # some dicom files don't have a valid header
                # force=True,
                # don't read huge fields, esp. if this isn't even really dicom
                defer_size=1024,
                # don't read image data, just metadata
                stop_before_pixels=True)
            # does this look like a dicom file?
            if (len(ds.dir()), len(ds.items())) == (0, 1):
                return data
            # human-readable keys
            for key in ds.dir():
                value = _coerce(ds.data_element(key).value)
                if value is not None:
                    data[key] = value
            # hex keys
            for key, value in ds.items():
                key = 'x%04x%04x' % (key.group, key.element)
                value = _coerce(value.value)
                if value is not None:
                    data[key] = value
    except dicom.errors.InvalidDicomError:
        # if this error occurs, probably not a dicom file
        return None
    return data


def _uploadHandler(event):
    """
    Whenever an additional file is uploaded to a "DICOM item", remove any
    DICOM metadata that is no longer common to all DICOM files in the item.
    """
    file = event.info['file']
    fileMetadata = _parseFile(file)
    if fileMetadata is None:
        return
    item = Item().load(file['itemId'], force=True)
    if 'dicom' in item:
        item['dicom']['meta'] = _removeUniqueMetadata(item['dicom']['meta'], fileMetadata)
    else:
        # In this case the uploaded file is the first of the item
        item['dicom'] = {
            'meta': fileMetadata,
            'files': []
        }
    item['dicom']['files'].append(_extractFileData(file, fileMetadata))
    item['dicom']['files'].sort(key=_getDicomFileSortKey)
    Item().save(item)
    events.trigger('dicom_viewer.upload.success')


def load(info):
    Item().exposeFields(level=AccessType.READ, fields={'dicom'})
    events.bind('data.process', 'dicom_viewer', _uploadHandler)
    dicomItem = DicomItem()
    info['apiRoot'].item.route(
        'POST', (':id', 'parseDicom'), dicomItem.makeDicomItem)
