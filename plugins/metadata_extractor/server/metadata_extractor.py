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
import six

from hachoir_core.error import HachoirError
from hachoir_metadata import extractMetadata
from hachoir_parser import createParser

try:
    from girder.utility.model_importer import ModelImporter

except ImportError:
    ModelImporter = None


class MetadataExtractor(object):
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
        Extract metadata from file on client or server using hachoir-metadata.
        """
        try:
            parser = createParser(six.text_type(self.path),
                                  six.binary_type(self.path))

            if parser is None:
                raise HachoirError('no parser')

            extractor = extractMetadata(parser)

            if extractor is None:
                raise HachoirError('no extractor')

            self.metadata = dict()

            for data in sorted(extractor):
                if not data.values:
                    continue

                key = data.description
                value = ', '.join([item.text for item in data.values])
                self.metadata[key] = value

        except HachoirError:
            self.metadata = None

    def _setMetadata(self):
        """
        Attach metadata to item on server.
        """
        pass


class ClientMetadataExtractor(MetadataExtractor):
    def __init__(self, client, path, itemId):
        """
        Initialize client metadata extractor.

        :param client: client instance
        :param path: path of file from which to extract metadata on remote
        client
        :param itemId: item ID of item containing file on server
        """
        super(ClientMetadataExtractor, self).__init__(path, itemId)
        self.client = client

    def _setMetadata(self):
        """
        Attach metadata to item on server.
        """
        super(ClientMetadataExtractor, self)._setMetadata()
        self.client.addMetadataToItem(str(self.itemId), self.metadata)


class ServerMetadataExtractor(MetadataExtractor, ModelImporter):
    def __init__(self, assetstore, uploadedFile):
        """
        Initialize server metadata extractor.

        :param assetstore: asset store containing file
        :param uploadedFile: file from which to extract metadata
        """
        path = os.path.join(assetstore['root'], uploadedFile['path'])
        super(ServerMetadataExtractor, self).__init__(path,
                                                      uploadedFile['itemId'])
        self.userId = uploadedFile['creatorId']

    def _setMetadata(self):
        """
        Attach metadata to item on server.

        """
        super(ServerMetadataExtractor, self)._setMetadata()
        item = self.model('item').load(self.itemId, force=True)
        self.model('item').setMetadata(item, self.metadata)
