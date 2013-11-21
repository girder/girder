#!/usr/bin/env python
# -*- coding: utf-8 -*-

###############################################################################
#  Copyright 2013 Kitware Inc.
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

import cherrypy
import os
import pymongo

#from .docs import assetstore_docs
from ..rest import Resource, RestException
from girder.constants import AssetstoreType


class Assetstore(Resource):
    """
    API Endpoint for managing assetstores. Requires admin privileges.
    """

    def find(self, params):
        """
        Get a list of assetstores.

        :param limit: The result set size limit, default=50.
        :param offset: Offset into the results, default=0.
        :param sort: The field to sort by, default=name.
        :param sortdir: 1 for ascending, -1 for descending, default=1.
        """
        limit, offset, sort = self.getPagingParameters(params, 'name')

        return self.model('assetstore').list(
            offset=offset, limit=limit, sort=sort)

    @Resource.endpoint
    def GET(self, path, params):
        self.requireAdmin(self.getCurrentUser())

        if not path:
            return self.find(params)
        else:
            raise Exception('Endpoint not implemented.')

    @Resource.endpoint
    def POST(self, path, params):
        """
        Create a new assetstore
        """
        self.requireAdmin(self.getCurrentUser())
        self.requireParams(['type', 'name'], params)

        assetstoreType = int(params['type'])

        if assetstoreType == AssetstoreType.FILESYSTEM:
            self.requireParams(['root'], params)
            return self.model('assetstore').createFilesystemAssetstore(
                name=params['name'], root=params['root'])
        elif assetstoreType == AssetstoreType.GRIDFS:
            self.requireParams(['db'], params)
            return self.model('assetstore').createGridFSAssetstore(
                name=params['name'], db=params['db'])
        elif assetstoreType == AssetstoreType.S3:
            return self.model('assetstore').createS3Assetstore(
                name=params['name'])
        else:
            raise RestException('Invalid type parameter')
