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

from girder.models.model_base import ValidationException
from girder.utility.abstract_assetstore_adapter import AbstractAssetstoreAdapter
from snakebite.client import Client as HdfsClient


class HdfsAssetstoreAdapter(AbstractAssetstoreAdapter):
    def __init__(self, assetstore):
        self.asserstore = assetstore
        self.client = self._getClient(assetstore)

    @staticmethod
    def _getClient(assetstore):
        return HdfsClient(
            host=assetstore['hdfs']['host'], port=assetstore['hdfs']['port'],
            use_trash=False)

    @staticmethod
    def validateInfo(doc):
        """
        Ensures we have the necessary information to connect to HDFS instance,
        and uses snakebite to actually connect to it.
        """
        info = doc.get('hdfs', {})
        for field in ('host', 'port', 'path'):
            if field not in info:
                raise ValidationException('Missing %s field.' % field)
        info['port'] = int(info['port'])

        try:
            client = HdfsAssetstoreAdapter._getClient(doc)
            client.serverdefaults()
        except:
            raise ValidationException('Could not connect to HDFS at %s:%d.' %
                                      (info['host'], info['port']))

        return doc

    def capacityInfo(self):
        info = self.client.df()
        return {
            'free': info['capacity'] - info['used'],
            'total': info['capacity']
        }
