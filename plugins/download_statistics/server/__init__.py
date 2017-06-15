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
from girder.constants import AccessType
from girder.utility.model_importer import ModelImporter


def downloadItemStartEvent(event):
    # Ony count download as started if offset is 0
    itemModel = ModelImporter.model('item')
    item = itemModel.load(event.info['id'], force=True)
    firstRequest = 'offset' not in event.info['params'] or event.info['params']['offset'] == '0'

    # Get all files in item to increment their download count
    files = itemModel.childFiles(item=item)
    for file in files:
        if firstRequest:
            downloadFileStart(file['_id'])
        downloadFileRequest(file['_id'])


def downloadFileStartEvent(event):
    # Ony count download as started if offset is 0
    fileModel = ModelImporter.model('file')
    file = fileModel.load(event.info['id'], force=True)
    firstRequest = 'offset' not in event.info['params'] or event.info['params']['offset'] == '0'

    if firstRequest:
        downloadFileStart(file['_id'])
    downloadFileRequest(file['_id'])


def downloadFileCompleteEvent(event):
    # WHAT TO SEND IN INFO FOR EVENT?
    fileModel = ModelImporter.model('file')
    file = fileModel.load(event.info['id'], force=True)
    downloadFileComplete(file['_id'])


def downloadFileStart(fileId):
    ModelImporter.model('file').increment(query={'_id': fileId},
                                          field='downloadStatistics.started', amount=1)


def downloadFileRequest(fileId):
    ModelImporter.model('file').increment(query={'_id': fileId},
                                          field='downloadStatistics.requested', amount=1)


def downloadFileComplete(fileId):
    ModelImporter.model('file').increment(query={'_id': fileId},
                                          field='downloadStatistics.completed', amount=1)


def load(info):
    # Bind REST events
    events.bind('rest.get.item/:id/download.before', 'download_statistics',
                downloadItemStartEvent)
    events.bind('rest.get.file/:id/download.before', 'download_statistics',
                downloadFileStartEvent)
    events.bind('download.complete', 'download_statistics',
                downloadFileCompleteEvent)

    # Add download count fields to file model
    downloadStatistics = {'started': 0,
                          'requested': 0,
                          'completed': 0}
    ModelImporter.model('file').exposeFields(level=AccessType.READ,
                                             fields=downloadStatistics)
