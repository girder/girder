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
from girder.constants import AssetstoreType
from girder.utility.model_importer import ModelImporter
from .assetstore import HdfsAssetstoreAdapter
from .rest import HdfsAssetstoreResource


def getAssetstore(event):
    assetstore = event.info
    if assetstore['type'] == AssetstoreType.HDFS:
        event.stopPropagation()
        event.addResponse(HdfsAssetstoreAdapter)


def updateAssetstore(event):
    params = event.info['params']
    assetstore = event.info['assetstore']

    if assetstore['type'] == AssetstoreType.HDFS:
        assetstore['hdfs'] = {
            'host': params['hdfsHost'],
            'port': params['hdfsPort'],
            'path': params['hdfsPath'],
            'webHdfsPort': params.get('webHdfsPort'),
            'user': params.get('hdfsUser')
        }


def createAssetstore(event):
    params = event.info['params']

    if params.get('type') == AssetstoreType.HDFS:
        event.addResponse(ModelImporter.model('assetstore').save({
            'type': AssetstoreType.HDFS,
            'name': params.get('name'),
            'hdfs': {
                'host': params.get('host'),
                'port': params.get('port'),
                'path': params.get('path'),
                'webHdfsPort': params.get('webHdfsPort'),
                'user': params.get('effectiveUser')
            }
        }))
        event.preventDefault()

def load(info):
    AssetstoreType.HDFS = 'hdfs'
    events.bind('assetstore.adapter.get', 'hdfs_assetstore', getAssetstore)
    events.bind('assetstore.update', 'hdfs_assetstore', updateAssetstore)
    events.bind('rest.post.assetstore.before', 'hdfs_assetstore',
                createAssetstore)

    info['apiRoot'].hdfs_assetstore = HdfsAssetstoreResource()
