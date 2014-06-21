#!/usr/bin/env python
# -*- coding: utf-8 -*-

###############################################################################
#  Copyright 2014 Kitware Inc.
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

import boto
import os

from .abstract_assetstore_adapter import AbstractAssetstoreAdapter
from girder.models.model_base import ValidationException
from girder import logger


class S3AssetstoreAdapter(AbstractAssetstoreAdapter):
    """
    This assetstore type stores files on S3. It is responsible for generating
    HMAC-signed messages that authorize the client to communicate directly with
    the S3 server where the files are stored.
    """

    @staticmethod
    def validateInfo(doc):
        """
        Makes sure the root field is a valid absolute path and is writeable.
        """
        if 'prefix' not in doc:
            doc['prefix'] = ''
        while len(doc['prefix']) and doc['prefix'][0] == '/':
            doc['prefix'] = doc['prefix'][1:]
        while len(doc['prefix']) and doc['prefix'][-1] == '/':
            doc['prefix'] = doc['prefix'][:-1]
        if not doc.get('bucket'):
            raise ValidationException('Bucket must not be empty.', 'bucket')
        if not doc.get('secret'):
            raise ValidationException(
                'Secret key must not be empty.', 'secretKey')
        if not doc.get('accessKeyId'):
            raise ValidationException(
                'Access key ID must not be empty.', 'accessKeyId')

        # Make sure we can write into the given bucket using boto
        try:
            conn = boto.connect_s3(aws_access_key_id=doc['accessKeyId'],
                                   aws_secret_access_key=doc['secret'])
            bucket = conn.lookup(bucket_name=doc['bucket'], validate=False)
            testKey = boto.s3.key.Key(
                bucket=bucket, name=os.path.join(doc['prefix'], 'test'))
            testKey.set_contents_from_string('')
        except:
            logger.exception('S3 assetstore validation exception')
            raise ValidationException('Unable to write into bucket "{}".'
                                      .format(doc['bucket']), 'bucket')

        return doc

    def __init__(self, assetstore):
        """
        :param assetstore: The assetstore to act on.
        """
        self.assetstore = assetstore

    def initUpload(self, upload):
        pass  # TODO

    def uploadChunk(self, upload, chunk):
        pass  # TODO

    def requestOffset(self, upload):
        pass  # TODO

    def finalizeUpload(self, upload, file):
        pass  # TODO

    def downloadFile(self, file, offset=0, headers=True):
        pass  # TODO

    def deleteFile(self, file):
        pass  # TODO
