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


def _onDownloadFileRequest(event):
    if event.info['startByte'] == 0:
        ModelImporter.model('file').increment(
            query={'_id': event.info['file']['_id']},
            field='downloadStatistics.started',
            amount=1)
    ModelImporter.model('file').increment(
        query={'_id': event.info['file']['_id']},
        field='downloadStatistics.requested',
        amount=1)


def _onDownloadFileComplete(event):
    ModelImporter.model('file').increment(
        query={'_id': event.info['file']['_id']},
        field='downloadStatistics.completed',
        amount=1)


def load(info):
    # Bind REST events
    events.bind('model.file.download.request', 'download_statistics', _onDownloadFileRequest)
    events.bind('model.file.download.complete', 'download_statistics', _onDownloadFileComplete)

    # Add download count fields to file model
    ModelImporter.model('file').exposeFields(level=AccessType.READ, fields='downloadStatistics')
