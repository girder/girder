# -*- coding: utf-8 -*-
import datetime
import json

import pydicom
import pydicom.valuerep
import pydicom.multival
import pydicom.sequence

from girder import events
from girder.api import access
from girder.api.describe import Description, autoDescribeRoute
from girder.api.rest import Resource
from girder.constants import AccessType, TokenScope
from girder.exceptions import RestException
from girder.plugin import GirderPlugin
from girder.models.item import Item
from girder.models.file import File
from girder.utility import search
from girder.utility.progress import setResponseTimeLimit


class DicomViewerPlugin(GirderPlugin):
    DISPLAY_NAME = 'DICOM Viewer'
    CLIENT_SOURCE_PATH = 'web_client'

    def load(self, info):
        Item().exposeFields(level=AccessType.READ, fields={'dicom'})
        events.bind('data.process', 'dicom_viewer', _uploadHandler)

        # Add the DICOM search mode only once
        search.addSearchMode('dicom', dicomSubstringSearchHandler)

        dicomItem = DicomItem()
        info['apiRoot'].item.route(
            'POST', (':id', 'parseDicom'), dicomItem.makeDicomItem)


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

            setResponseTimeLimit()

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


def _extractFileData(file, dicomMetadata):
    """
    Extract the useful data to be stored in the `item['dicom']['files']`.
    In this way it become simpler to sort them and store them.
    """
    return {
        'dicom': {
            'SeriesNumber': dicomMetadata.get('SeriesNumber'),
            'InstanceNumber': dicomMetadata.get('InstanceNumber'),
            'SliceLocation': dicomMetadata.get('SliceLocation')
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
            for k, v in dicomMeta.items()
        )
        & set(
            (
                k,
                tuple(v) if isinstance(v, list) else v
            )
            for k, v in additionalMeta.items()
        )
    )


def _coerceValue(value):
    # For binary data, see if it can be coerced further into utf8 data.  If
    # not, mongo won't store it, so don't accept it here.
    if isinstance(value, bytes):
        if b'\x00' in value:
            raise ValueError('Binary data with null')
        try:
            value.decode('utf-8')
        except UnicodeDecodeError:
            raise ValueError('Binary data that cannot be stored as utf-8')
    # Many pydicom value types are subclasses of base types; to ensure the value can be serialized
    # to MongoDB, cast the value back to its base type
    for knownBaseType in {
        int,
        float,
        bytes,
        str,
        datetime.datetime,
        datetime.date,
        datetime.time,
    }:
        if isinstance(value, knownBaseType):
            return knownBaseType(value)

    # pydicom does not treat the PersonName type as a subclass of a text type
    if isinstance(value, pydicom.valuerep.PersonName):
        return value.encode('utf-8')

    # Handle lists (MultiValue) recursively
    if isinstance(value, pydicom.multival.MultiValue):
        if isinstance(value, pydicom.sequence.Sequence):
            # A pydicom Sequence is a nested list of Datasets, which is too complicated to flatten
            # now
            raise ValueError('Cannot coerce a Sequence')
        return list(map(_coerceValue, value))

    raise ValueError('Unknown type', type(value))


def _coerceMetadata(dataset):
    metadata = {}

    # Use simple iteration instead of "dataset.iterall", to prevent recursing into Sequences, which
    # are too complicated to flatten now
    # The dataset iterator is
    #   for tag in sorted(dataset.keys()):
    #       yield dataset[tag]
    # but we want to ignore certain exceptions of delayed data loading, so
    # we iterate through the dataset ourselves.
    for tag in dataset.keys():
        try:
            dataElement = dataset[tag]
        except IOError:
            continue
        if dataElement.tag.element == 0:
            # Skip Group Length tags, which are always element 0x0000
            continue

        # Use "keyword" instead of "name", as the keyword is a simpler and more uniform string
        # See: http://dicom.nema.org/medical/dicom/current/output/html/part06.html#table_6-1
        # For unknown / private tags, allow pydicom to create a string representation like
        # "(0013, 1010)"
        tagKey = dataElement.keyword \
            if dataElement.keyword and not dataElement.tag.is_private else \
            str(dataElement.tag)

        try:
            tagValue = _coerceValue(dataElement.value)
        except ValueError:
            # Omit tags where the value cannot be coerced to JSON-encodable types
            continue

        metadata[tagKey] = tagValue

    return metadata


def _parseFile(f):
    try:
        # download file and try to parse dicom
        with File().open(f) as fp:
            dataset = pydicom.dcmread(
                fp,
                # don't read huge fields, esp. if this isn't even really dicom
                defer_size=1024,
                # don't read image data, just metadata
                stop_before_pixels=True)
            return _coerceMetadata(dataset)
    except pydicom.errors.InvalidDicomError:
        # if this error occurs, probably not a dicom file
        return None


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


def dicomSubstringSearchHandler(query, types, user=None, level=None, limit=0, offset=0):
    """
    Provide a substring search on both keys and values.
    """
    if types != ['item']:
        raise RestException('The dicom search is only able to search in Item.')
    if not isinstance(query, str):
        raise RestException('The search query must be a string.')

    jsQuery = """
        function() {
            var queryKey = %(query)s.toLowerCase();
            var queryValue = queryKey;
            var dicomMeta = obj.dicom.meta;
            return Object.keys(dicomMeta).some(
                function(key) {
                    return (key.toLowerCase().indexOf(queryKey) !== -1)  ||
                        dicomMeta[key].toString().toLowerCase().indexOf(queryValue) !== -1;
                })
            }
    """ % {
        # This could eventually be a separately-defined key and value
        'query': json.dumps(query)
    }

    # Sort the documents inside MongoDB
    cursor = Item().find({'dicom': {'$exists': True}, '$where': jsQuery})
    # Filter the result
    result = {
        'item': [
            Item().filter(doc, user)
            for doc in Item().filterResultsByPermission(cursor, user, level, limit, offset)
        ]
    }

    return result
