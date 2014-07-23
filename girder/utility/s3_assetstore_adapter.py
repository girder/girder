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
import json
import os
import time
import urllib
import uuid

from .abstract_assetstore_adapter import AbstractAssetstoreAdapter
from girder.models.model_base import ValidationException
from girder import logger, events


class S3AssetstoreAdapter(AbstractAssetstoreAdapter):
    """
    This assetstore type stores files on S3. It is responsible for generating
    HMAC-signed messages that authorize the client to communicate directly with
    the S3 server where the files are stored.
    """

    CHUNK_LEN = 1024 * 1024 * 32  # Chunk size for uploading
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
    def fileIndexFields():
        """
        File documents should have an index on their verified field.
        """
        return ['s3Verified']

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

    def _getRequestHeaders(self, upload):
        headers = {
            'Content-Disposition': 'attachment; filename="{}"'
                                   .format(upload['name'])
        }
        signedHeaders = {
            'x-amz-acl': 'private',
            'x-amz-meta-authorized-length': upload['size'],
            'x-amz-meta-uploader-id': upload['userId'],
            'x-amz-meta-uploader-ip': cherrypy.request.remote.ip
        }
        canonicalHeaders = '\n'.join(
            map(lambda (k, v): '{}:{}'.format(k, v),
                sorted(signedHeaders.items())))

        allHeaders = dict(headers)
        allHeaders.update(signedHeaders)

        return canonicalHeaders, allHeaders

    def initUpload(self, upload):
        """
        Build the request required to initiate an authorized upload to S3.
        """
        if upload['size'] <= 0:
            return upload

        uid = uuid.uuid4().hex
        expires = int(time.time() + self.HMAC_TTL)
        key = os.path.join(self.assetstore.get('prefix', ''),
                           uid[0:2], uid[2:4], uid)
        path = '/{}/{}'.format(self.assetstore['bucket'], key)
        canonical, allHeaders = self._getRequestHeaders(upload)

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
            'relpath': path,
            'key': key
        }

        if chunked:
            signature = self._getSignature(
                ('POST', '', '', expires, canonical, path + '?uploads'))
            url += '&uploads&Signature=' + urllib.quote(signature)

            upload['s3']['request'] = {
                'method': 'POST',
                'url': url,
                'headers': allHeaders
            }
        else:
            signature = self._getSignature(
                ('PUT', '', upload['mimeType'], expires, canonical, path))
            url += '&Signature=' + urllib.quote(signature)

            upload['s3']['request'] = {
                'method': 'PUT',
                'url': url,
                'headers': allHeaders
            }

        return upload

    def uploadChunk(self, upload, chunk):
        """
        Rather than processing actual bytes of the chunk, this will generate
        the signature required to upload the chunk.

        :param chunk: This should be a JSON string containing the chunk number
        and S3 upload ID.
        """
        info = json.loads(chunk)
        expires = int(time.time() + self.HMAC_TTL)
        queryStr = '?partNumber={}&uploadId={}'.format(
            info['partNumber'], info['s3UploadId'])
        sig = self._getSignature(
            ('PUT', '', '', expires, upload['s3']['relpath'] + queryStr))
        url = (
            'https://{}.s3.amazonaws.com/{}{}&Expires={}&AWSAccessKeyId={}'
            '&Signature={}').format(
            self.assetstore['bucket'], upload['s3']['key'], queryStr,
            expires, self.assetstore['accessKeyId'], urllib.quote(sig))

        upload['s3']['uploadId'] = info['s3UploadId']
        upload['s3']['partNumber'] = info['partNumber']
        upload['s3']['request'] = {
            'method': 'PUT',
            'url': url
        }
        return upload

    def requestOffset(self, upload):
        if upload['s3']['chunked']:
            raise ValidationException('Do not call requestOffset on a chunked '
                                      'S3 upload.')

        expires = int(time.time() + self.HMAC_TTL)
        canonical, allHeaders = self._getRequestHeaders(upload)
        signature = self._getSignature(('PUT', '', upload['mimeType'], expires,
                                        canonical, upload['s3']['relpath']))
        url = '{}?Expires={}&AWSAccessKeyId={}&Signature={}'.format(
            upload['s3']['fullpath'], expires, self.assetstore['accessKeyId'],
            urllib.quote(signature))

        return {
            'method': 'PUT',
            'url': url,
            'headers': allHeaders
        }

    def finalizeUpload(self, upload, file):
        if upload['size'] <= 0:
            return file

        file['fullpath'] = upload['s3']['fullpath']
        file['relpath'] = upload['s3']['relpath']
        file['s3Key'] = upload['s3']['key']
        file['s3Verified'] = False

        if upload['s3']['chunked']:
            expires = int(time.time() + self.HMAC_TTL)
            queryStr = '?uploadId=' + upload['s3']['uploadId']
            contentType = 'text/plain;charset=UTF-8'

            signature = self._getSignature(
                ('POST', '', contentType, expires,
                 upload['s3']['relpath'] + queryStr))
            url = (
                'https://{}.s3.amazonaws.com/{}{}&Expires={}&AWSAccessKeyId={}'
                '&Signature={}').format(
                self.assetstore['bucket'], upload['s3']['key'], queryStr,
                expires, self.assetstore['accessKeyId'],
                urllib.quote(signature))

            file['s3FinalizeRequest'] = {
                'method': 'POST',
                'url': url,
                'headers': {
                    'Content-Type': 'text/plain;charset=UTF-8'
                }
            }

        return file

    def downloadFile(self, file, offset=0, headers=True):
        if headers:
            if file['size'] > 0:
                expires = int(time.time() + self.HMAC_TTL)
                signature = self._getSignature(
                    ('GET', '', '', expires, file['relpath']))
                url = '{}?Expires={}&AWSAccessKeyId={}&Signature={}'.format(
                    file['fullpath'], expires,
                    self.assetstore['accessKeyId'], urllib.quote(signature))
                raise cherrypy.HTTPRedirect(url)
            else:
                cherrypy.response.headers['Content-Length'] = '0'
                cherrypy.response.headers['Content-Type'] = \
                    'application/octet-stream'
                cherrypy.response.headers['Content-Disposition'] = \
                    'attachment; filename="{}"'.format(file['name'])

                def stream():
                    yield ''
                return stream
        else:  # Can't really support archive file downloading for S3 files
            def stream():
                yield '==S3==\n{}'.format(file['fullpath'])
            return stream

    def deleteFile(self, file):
        """
        We want to queue up files to be deleted asynchronously since it requires
        an external HTTP request per file in order to delete them, and we don't
        want to wait on that.
        """
        if file['size'] > 0:
            events.daemon.trigger('_s3_assetstore_delete_file', {
                'accessKeyId': self.assetstore['accessKeyId'],
                'secret': self.assetstore['secret'],
                'bucket': self.assetstore['bucket'],
                'key': file['s3Key']
            })


def _deleteFileImpl(event):
    """
    Uses boto to delete the key.
    """
    info = event.info
    conn = boto.connect_s3(aws_access_key_id=info['accessKeyId'],
                           aws_secret_access_key=info['secret'])
    bucket = conn.lookup(bucket_name=info['bucket'], validate=False)
    key = boto.s3.key.Key(bucket=bucket, name=info['key'])
    bucket.delete_key(key)


events.bind('_s3_assetstore_delete_file', '_s3_assetstore_delete_file',
            _deleteFileImpl)
