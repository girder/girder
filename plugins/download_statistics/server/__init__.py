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
from girder.models.item import Item
from girder.models.file import File


def downloadItemStartEvent(event):
    # Ony count download as started if offset is 0
    itemModel = Item()
    item = itemModel.load(event.info['id'], force=True)
    firstRequest = 'offset' not in event.info['params'] or event.info['params']['offset'] == '0'

    # Get all files in item to increment their download count
    files = list(itemModel.childFiles(item=item))
    for file in files:
        if firstRequest:
            downloadFileStart(file['_id'])
        downloadFileRequest(file['_id'])


def downloadItemCompleteEvent(event):
    itemModel = Item()
    item = itemModel.load(event.info['id'], force=True)

    # Get all files in item to increment their download count
    files = list(itemModel.childFiles(item=item))
    for file in files:
        downloadFileComplete(file['_id'])


def downloadFileStartEvent(event):
    # Ony count download as started if offset is 0
    fileModel = File()
    file = fileModel.load(event.info['id'], force=True)
    firstRequest = 'offset' not in event.info['params'] or event.info['params']['offset'] == '0'

    if firstRequest:
        downloadFileStart(file['_id'])
    downloadFileRequest(file['_id'])


def downloadFileCompleteEvent(event):
    fileModel = File()
    file = fileModel.load(event.info['id'], force=True)
    downloadFileComplete(file['_id'])


def downloadFileStart(fileId):
    File().increment(query={'_id': fileId}, field='downloadsStarted', amount=1, multi=False)


def downloadFileRequest(fileId):
    File().increment(query={'_id': fileId}, field='downloadsRequested', amount=1, multi=False)


def downloadFileComplete(fileId):
    File().increment(query={'_id': fileId}, field='downloadsCompleted', amount=1, multi=False)


def load(info):
    # Bind REST events
    events.bind('rest.get.item/:id/download.before', 'download_statistics',
                downloadItemStartEvent)
    events.bind('rest.get.item/:id/download.after', 'download_statistics',
                downloadItemCompleteEvent)
    events.bind('rest.get.file/:id/download.before', 'download_statistics',
                downloadFileStartEvent)
    events.bind('rest.get.file/:id/download.after', 'download_statistics',
                downloadFileCompleteEvent)

    # Add download count fields to file model
    File().exposeFields(level=AccessType.READ,
                        fields=('downloadsStarted', 'downloadsRequested', 'downloadsCompleted'))
