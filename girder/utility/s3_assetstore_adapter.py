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

import base64
import boto
import cherrypy
import hashlib
import hmac
import os
import time
import urllib
import uuid

from .abstract_assetstore_adapter import AbstractAssetstoreAdapter
from girder.models.model_base import ValidationException
from girder import logger


class S3AssetstoreAdapter(AbstractAssetstoreAdapter):
    """
    This assetstore type stores files on S3. It is responsible for generating
    HMAC-signed messages that authorize the client to communicate directly with
    the S3 server where the files are stored.
    """

    CHUNK_LEN = 1024 * 1024 * 40  # Chunk size for uploading
    HMAC_TTL = 120  # Number of seconds each signed message is valid

    def _getSignature(self, msg):
        """
        Provide a message to HMAC-sign in the form of a string or list of
        lines.
        """
        if not isinstance(msg, basestring):
            msg = '\n'.join(map(str, msg))

        return base64.b64encode(hmac.new(
            str(self.assetstore['secret']),
            msg, hashlib.sha1).digest())

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
        """
        Build the request required to initiate an authorized upload to S3.
        """
        uid = uuid.uuid4().hex
        expires = int(time.time() + self.HMAC_TTL)
        key = os.path.join(self.assetstore.get('prefix', ''),
                           uid[0:2], uid[2:4], uid)
        path = '/{}/{}'.format(self.assetstore['bucket'], key)
        headers = '\n'.join(('x-amz-acl:private',))
        fullpath = 'https://{}.s3.amazonaws.com/{}'.format(
            self.assetstore['bucket'], key)
        url = '{}?Expires={}&AWSAccessKeyId={}'.format(
            fullpath, expires, self.assetstore['accessKeyId'])

        chunked = upload['size'] > self.CHUNK_LEN

        upload['behavior'] = 's3'
        upload['s3'] = {
            'chunked': chunked,
            'chunkLength': self.CHUNK_LEN,
            'fullpath': fullpath,
            'relpath': path
        }

        if chunked:
            signature = self._getSignature(
                ('POST', '', '', expires, headers, path + '?uploads'))
            url += '&uploads&Signature=' + urllib.quote(signature)

            upload['s3']['request'] = {
                'method': 'POST',
                'url': url,
                'headers': {
                    'x-amz-acl': 'private'
                }
            }
        else:
            signature = self._getSignature(
                ('PUT', '', upload['mimeType'], expires, headers, path))
            url += '&Signature=' + urllib.quote(signature)

            upload['s3']['request'] = {
                'method': 'PUT',
                'url': url,
                'headers': {
                    'x-amz-acl': 'private'
                }
            }

        return upload

    def uploadChunk(self, upload, chunk):
        pass  # TODO

    def requestOffset(self, upload):
        raise Exception('S3 assetstore does not support requestOffset.')

    def finalizeUpload(self, upload, file):
        file['fullpath'] = upload['s3']['fullpath']
        file['relpath'] = upload['s3']['relpath']
        return file

    def downloadFile(self, file, offset=0, headers=True):
        if headers:
            expires = int(time.time() + self.HMAC_TTL)
            signature = self._getSignature(
                ('GET', '', '', expires, file['relpath']))
            url = '{}?Expires={}&AWSAccessKeyId={}&Signature={}'.format(
                file['fullpath'], expires,
                self.assetstore['accessKeyId'], signature)
            raise cherrypy.HTTPRedirect(url)
        else:
            def stream():
                yield 'S3 File: {}'.format(file['fullpath'])

    def deleteFile(self, file):
        pass  # TODO
