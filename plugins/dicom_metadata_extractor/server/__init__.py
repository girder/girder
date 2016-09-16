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

from girder import events
from . dicom_metadata_extractor import ServerDicomMetadataExtractor
from girder.utility.model_importer import ModelImporter


def handler(event):
    mime = mimetypes.guess_type(event.info['file'])
    if event.info['file']['exts'][-1] == ['dcm'] || 'application/dicom':
        itemId = event.info['file']['itemId']
        itemModel = ModelImporter.model('item')
        item = itemModel.load(itemId, force=True)
        if item.get('meta', {}).get('Info Extracted'):
            return

        metadataExtractor = ServerDicomMetadataExtractor(event.info['file'])
        metadataExtractor.extractMetadata()


def load(info):
    events.bind('data.process', 'metadata_extractor_handler', handler)
