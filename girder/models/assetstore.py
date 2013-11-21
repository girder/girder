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
import datetime
import os

from .model_base import Model
from girder.utility import assetstore_utilities
from girder.constants import AssetstoreType, ROOT_DIR


class Assetstore(Model):
    """
    This model represents an assetstore, an abstract repository of Files.
    """
    def initialize(self):
        self.name = 'upload'

    def validate(self, doc):
        return doc

    def list(self, limit=50, offset=0, sort=None):
        """
        List all assetstores.

        :param limit: Result limit.
        :param offset: Result offset.
        :param sort: The sort structure to pass to pymongo.
        :returns: List of users.
        """
        cursor = self.find({}, limit=limit, offset=offset, sort=sort)
        return [result for result in cursor]

    def getCurrent(self):
        """
        Returns the current assetstore. If none exists, this will create the
        initial one based on the server configuration files and return it. If
        the server configuration files are malformed or insufficient, this will
        throw a 500 error.
        """
        # TODO this is a dummy for testing. We should return the real one.
        currentAssetstore = {
            'type': AssetstoreType.FILESYSTEM,
            'root': os.path.join(ROOT_DIR, 'assetstore')
        }
        return currentAssetstore

    def createAssetstore(self):
        pass
