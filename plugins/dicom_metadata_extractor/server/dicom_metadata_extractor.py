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

try:
    from girder.utility.model_importer import ModelImporter

except ImportError:
    ModelImporter = None


class DicomMetadataExtractor(object):
    def __init__(self, path, itemId):
        """
        Initialize the metadata extractor.

        :param path: path of file from which to extract metadata on client or
        server
        :param itemId: item ID of item containing file on server
        """
        self.itemId = itemId
        self.path = path
        self.metadata = None

    def extractMetadata(self):
        """
        Extract metadata from file on client or server and attach to item on
        server.
        """
        self._extractMetadata()

        if self.metadata is not None:
            self._setMetadata()

    def _extractMetadata(self):
        """
        Extract metadata from file on client or server using hachoir-metadata
        or pydicom for DICOM images.
        """

        try:
            dcMetadata = dicom.read_file(self.path, stop_before_pixels=True)
            if dcMetadata:
                self.metadata = dict()
                for item in dcMetadata:
                    # pass forces rawDataElement to DataElement conversion
                    pass
                    if not item.tag.is_private:
                        name = str(item.name).replace('.', '')
                        value = str(item.value)
                        self.metadata[name] = value
                self.metadata['Info Extracted'] = True
            else:
                self.metadata = None

        except dicom.filereader.InvalidDicomError:
            self.metadata = None

    def _setMetadata(self):
        """
        Attach metadata to item on server.
        """
        pass


class ClientDicomMetadataExtractor(DicomMetadataExtractor):
    def __init__(self, client, fileId, itemId):
        """
        Initialize client metadata extractor.

        :param client: client instance
        :param fileId: file ID of file from which to extract metadata
        :param itemId: item ID of item containing file on server

        """
        output = six.BytesIO()
        client.downloadFile(fileId, output)
        output.seek(0)
        super(ClientDicomMetadataExtractor, self).__init__(output, itemId)
        self.client = client

    def _setMetadata(self):
        """
        Attach metadata to item on server.
        """
        super(ClientDicomMetadataExtractor, self)._setMetadata()
        self.client.addMetadataToItem(str(self.itemId), self.metadata)


class ServerDicomMetadataExtractor(DicomMetadataExtractor, ModelImporter):
    def __init__(self, uploadedFile):
        """
        Initialize server metadata extractor.

        :param assetstore: asset store containing file
        :param uploadedFile: file from which to extract metadata

        """
        stream = ModelImporter.model('file').download(uploadedFile, headers=False)
        output = six.BytesIO(b''.join(stream()))
        super(ServerDicomMetadataExtractor, self).__init__(output, uploadedFile['itemId'])
        self.userId = uploadedFile['creatorId']

    def _setMetadata(self):
        """
        Attach metadata to item on server.

        """
        super(ServerDicomMetadataExtractor, self)._setMetadata()
        item = self.model('item').load(self.itemId, force=True)
        self.model('item').setMetadata(item, self.metadata)
