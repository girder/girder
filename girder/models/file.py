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

from .model_base import Model, ValidationException
from girder.utility import assetstore_adapter_factory


class File(Model):
    """
    This model represents a File, which is stored in an assetstore.
    """
    def initialize(self):
        self.name = 'file'
        self.assetstoreAdapter =\
            assetstore_adapter_factory.getAssetstoreAdapter()

    def remove(self, file):
        self.assetstoreAdapter.deleteFile(file)
        Model.remove(self, file)

    def validate(self, doc):
        return doc

    def createFile(self, creator, item, name, size):
        """
        Create a new file record in the database.
        :param item: The parent item.
        :param creator: The user creating the file.
        :param name: The filename.
        :type name: str
        :param size: The size of the file in bytes.
        :type size: int
        """
        file = {
            'created': datetime.datetime.now(),
            'itemId': item['_id'],
            'creatorId': creator['_id'],
            #'assetstoreId': TODO get current assetstore Id
            'name': name,
            'size': size
        }
        return self.save(file)
