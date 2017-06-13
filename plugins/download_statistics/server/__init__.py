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

import rpdb

def downloadItemStartEvent(event):
    # TODO Find which file is being downloaded with this item.
    if 'offset' not in event.info['params'] or event.info['params']['offset'] == '0':
        rpdb.set_trace()
        itemModel = Item()
        item = itemModel.load(event.info['id'], force=True)
        files = list(itemModel.childFiles(item=item, limit=2))
        for file in files:
            downloadFileStart(file['_id'])

def downloadItemCompleteEvent(event):
    # TODO Find which file is being downloaded with this item.
    itemModel = Item()
    item = itemModel.load(event.info['id'], force=True)
    files = list(itemModel.childFiles(item=item, limit=2))
    for file in files:
        downloadFileComplete(fileId)

def downloadFileStartEvent(event):
    # TODO Get fileId from event
    if 'offset' not in event.info['params'] or event.info['params']['offset'] == '0':
        rpdb.set_trace()
        fileModel = File()
        file = fileModel.load(event.info['id'], force=True)
        downloadFileStart(file['_id'])

def downloadFileCompleteEvent(event):
    # TODO Get fileId from event
    fileModel = File()
    file = fileModel.load(event.info['id'], force=True)
    downloadFileComplete(file['_id'])

def downloadFileStart(fileId):
    File().increment(query={'_id': fileId}, field='downloadsStarted', amount=1, multi=False)

def downloadFileComplete(fileId):
    File().increment(query={'_id': fileId}, field='downloadsCompleted', amount=1, multi=False)

def load(info):
    # Bind REST events
    events.bind('rest.get.item/:id/download.before', 'download_statistics', downloadItemStartEvent)
    events.bind('rest.get.item/:id/download.after', 'download_statistics', downloadItemCompleteEvent)
    events.bind('rest.get.file/:id/download.before', 'download_statistics', downloadFileStartEvent)
    events.bind('rest.get.file/:id/download.after', 'download_statistics', downloadFileCompleteEvent)

    # Add download count field to file model
    File().exposeFields(level=AccessType.READ, fields='downloadsStarted')
    File().exposeFields(level=AccessType.READ, fields='downloadsCompleted')