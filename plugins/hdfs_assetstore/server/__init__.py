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

from .assetstore import HdfsAssetstoreAdapter
from .rest import HdfsAssetstoreResource
from girder import events
from girder.api import access
from girder.api.v1.assetstore import Assetstore
from girder.constants import AssetstoreType
from girder.utility.model_importer import ModelImporter
from girder.utility import assetstore_utilities


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
            'host': params.get('hdfsHost', assetstore['hdfs']['host']),
            'port': params.get('hdfsPort', assetstore['hdfs']['port']),
            'path': params.get('hdfsPath', assetstore['hdfs']['path']),
            'webHdfsPort': params.get('webHdfsPort',
                                      assetstore['hdfs'].get('webHdfsPort')),
            'user': params.get('hdfsUser', assetstore['hdfs'].get('user'))
        }


@access.admin
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
    events.bind('assetstore.update', 'hdfs_assetstore', updateAssetstore)
    events.bind('rest.post.assetstore.before', 'hdfs_assetstore',
                createAssetstore)

    assetstore_utilities.setAssetstoreAdapter(AssetstoreType.HDFS, HdfsAssetstoreAdapter)

    (Assetstore.createAssetstore.description
        .param('host', 'The namenode host (for HDFS type).', required=False)
        .param('port', 'The namenode RPC port (for HDFS type).', required=False)
        .param('path', 'Absolute path under which new files will be stored ('
               'for HDFS type).', required=False)
        .param('user', 'The effective user to use when calling HDFS RPCs (for '
               'HDFS type). This defaults to whatever system username the '
               'Girder server process is running under.', required=False)
        .param('webHdfsPort', 'WebHDFS port for the namenode. You must enable '
               'WebHDFS on your Hadoop cluster if you want to write new files '
               'to the assetstore (for HDFS type).', required=False))

    info['apiRoot'].hdfs_assetstore = HdfsAssetstoreResource()
