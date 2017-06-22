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


def downloadFileDuringEvent(event):
    downloadFileRequest(event.info['file']['_id'])


def downloadFileStartEvent(event):
    fileId = event.info['file']['_id']
    downloadFileStart(fileId)
    downloadFileRequest(fileId)


def downloadFileCompleteEvent(event):
    downloadFileComplete(event.info['file']['_id'])


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
    events.bind('model.file.download.before', 'download_statistics',
                downloadFileStartEvent)
    events.bind('model.file.download.during', 'download_statistics',
                downloadFileDuringEvent)
    events.bind('model.file.download.after', 'download_statistics',
                downloadFileCompleteEvent)

    # Add download count fields to file model
    ModelImporter.model('file').exposeFields(level=AccessType.READ,
                                             fields='downloadStatistics')
