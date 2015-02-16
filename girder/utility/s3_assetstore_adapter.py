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
import boto.s3.connection
import cherrypy
import json
import re
import requests
import uuid

from .abstract_assetstore_adapter import AbstractAssetstoreAdapter
from .model_importer import ModelImporter
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
        # remove slashes from front and back of the prefix
        doc['prefix'] = doc['prefix'].strip('/')
        if not doc.get('bucket'):
            raise ValidationException('Bucket must not be empty.', 'bucket')
        if not doc.get('secret'):
            raise ValidationException(
                'Secret key must not be empty.', 'secret')
        if not doc.get('accessKeyId'):
            raise ValidationException(
                'Access key ID must not be empty.', 'accessKeyId')
        # construct a set of connection parameters based on the keys and the
        # service
        if 'service' not in doc:
            doc['service'] = ''
        if doc['service'] != '':
            service = re.match("^((https?)://)?([^:/]+)(:([0-9]+))?$",
                               doc['service'])
            if not service:
                raise ValidationException(
                    'The service must of the form [http[s]://](host domain)'
                    '[:(port)].', 'service')
        doc['botoConnect'] = makeBotoConnectParams(
            doc['accessKeyId'], doc['secret'], doc['service'])
        # Make sure we can write into the given bucket using boto
        conn = botoConnectS3(doc['botoConnect'])
        try:
            bucket = conn.lookup(bucket_name=doc['bucket'], validate=True)
            testKey = boto.s3.key.Key(
                bucket=bucket, name='/'.join(
                    filter(None, (doc['prefix'], 'test'))))
            testKey.set_contents_from_string('')
        except Exception:
            logger.exception('S3 assetstore validation exception')
            raise ValidationException('Unable to write into bucket "{}".'
                                      .format(doc['bucket']), 'bucket')

        return doc

    def __init__(self, assetstore):
        """
        :param assetstore: The assetstore to act on.
        """
        if ('accessKeyId' in assetstore and 'secret' in assetstore and
                'service' in assetstore):
            assetstore['botoConnect'] = makeBotoConnectParams(
                assetstore['accessKeyId'], assetstore['secret'],
                assetstore['service'])
        self.assetstore = assetstore

    def _getRequestHeaders(self, upload):
        headers = {
            'Content-Disposition': 'attachment; filename="{}"'
                                   .format(upload['name']),
            'Content-Type': upload.get('mimeType', ''),
            'x-amz-acl': 'private',
            'x-amz-meta-authorized-length': str(upload['size']),
            'x-amz-meta-uploader-id': str(upload['userId']),
            'x-amz-meta-uploader-ip': str(cherrypy.request.remote.ip)
        }
        return headers

    def initUpload(self, upload):
        """
        Build the request required to initiate an authorized upload to S3.
        """
        if upload['size'] <= 0:
            return upload

        uid = uuid.uuid4().hex
        key = '/'.join(filter(None, (self.assetstore.get('prefix', ''),
                       uid[0:2], uid[2:4], uid)))
        path = '/{}/{}'.format(self.assetstore['bucket'], key)
        headers = self._getRequestHeaders(upload)

        chunked = upload['size'] > self.CHUNK_LEN

        upload['behavior'] = 's3'
        upload['s3'] = {
            'chunked': chunked,
            'chunkLength': self.CHUNK_LEN,
            'relpath': path,
            'key': key
        }

        if chunked:
            upload['s3']['request'] = {'method': 'POST'}
            queryParams = 'uploads'
        else:
            upload['s3']['request'] = {'method': 'PUT'}
            queryParams = None
        url = self._botoGenerateUrl(
            method=upload['s3']['request']['method'], key=key, headers=headers,
            queryParams=queryParams)
        upload['s3']['request']['url'] = url
        upload['s3']['request']['headers'] = headers
        return upload

    def uploadChunk(self, upload, chunk):
        """
        Rather than processing actual bytes of the chunk, this will generate
        the signature required to upload the chunk.

        :param chunk: This should be a JSON string containing the chunk number
        and S3 upload ID.
        """
        info = json.loads(chunk)
        queryStr = 'partNumber={}&uploadId={}'.format(info['partNumber'],
                                                      info['s3UploadId'])
        url = self._botoGenerateUrl(method='PUT', key=upload['s3']['key'],
                                    queryParams=queryStr)

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

        headers = self._getRequestHeaders(upload)
        url = self._botoGenerateUrl(method='PUT', key=upload['s3']['key'],
                                    headers=headers)
        return {
            'method': 'PUT',
            'url': url,
            'headers': headers
        }

    def finalizeUpload(self, upload, file):
        if upload['size'] <= 0:
            return file

        file['relpath'] = upload['s3']['relpath']
        file['s3Key'] = upload['s3']['key']
        file['s3Verified'] = False

        if upload['s3']['chunked']:
            queryStr = 'uploadId=' + upload['s3']['uploadId']
            headers = {'Content-Type': 'text/plain;charset=UTF-8'}
            url = self._botoGenerateUrl(method='POST', key=upload['s3']['key'],
                                        headers=headers, queryParams=queryStr)
            file['s3FinalizeRequest'] = {
                'method': 'POST',
                'url': url,
                'headers': headers
            }
        return file

    def downloadFile(self, file, offset=0, headers=True):
        """
        When downloading a single file with HTTP, we redirect to S3. Otherwise,
        e.g. when downloading as part of a zip stream, we connect to S3 and
        pipe the bytes from S3 through the server to the user agent.
        """
        if headers:
            if file['size'] > 0:
                url = self._botoGenerateUrl(key=file['s3Key'])
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
        else:
            def stream():
                if file['size'] > 0:
                    pipe = requests.get(
                        self._botoGenerateUrl(key=file['s3Key']), stream=True)
                    for chunk in pipe.iter_content(chunk_size=65536):
                        if chunk:
                            yield chunk
                else:
                    yield ''
            return stream

    def deleteFile(self, file):
        """
        We want to queue up files to be deleted asynchronously since it requires
        an external HTTP request per file in order to delete them, and we don't
        want to wait on that.
        """
        if file['size'] > 0 and 'relpath' in file:
            q = {
                'relpath': file['relpath'],
                'assetstoreId': self.assetstore['_id']
            }
            matching = ModelImporter().model('file').find(q, limit=2, fields=[])
            if matching.count(True) == 1:
                events.daemon.trigger('_s3_assetstore_delete_file', {
                    'botoConnect': self.assetstore.get('botoConnect', {}),
                    'bucket': self.assetstore['bucket'],
                    'key': file['s3Key']
                })

    def cancelUpload(self, upload):
        """
        Delete the temporary files associated with a given upload.
        """
        if 's3' not in upload:
            return
        if 'key' not in upload['s3']:
            return
        conn = botoConnectS3(self.assetstore.get('botoConnect', {}))
        bucket = conn.lookup(bucket_name=self.assetstore['bucket'],
                             validate=True)
        if bucket:
            key = bucket.get_key(upload['s3']['key'], validate=True)
            if key:
                bucket.delete_key(key)
            # check if this is an abandoned multipart upload
            if ('s3' in upload and 'uploadId' in upload['s3'] and
                    'key' in upload['s3']):
                getParams = {}
                while True:
                    try:
                        multipartUploads = bucket.get_all_multipart_uploads(
                            **getParams)
                    except boto.exception.S3ResponseError:
                        break
                    if not len(multipartUploads):
                        break
                    for multipartUpload in multipartUploads:
                        if (multipartUpload.id == upload['s3']['uploadId'] and
                                multipartUpload.key_name ==
                                upload['s3']['key']):
                            multipartUpload.cancel_upload()
                    if not multipartUploads.is_truncated:
                        break
                    getParams['key_marker'] = multipartUploads.next_key_marker
                    getParams['upload_id_marker'] = \
                        multipartUploads.next_upload_id_marker

    def untrackedUploads(self, knownUploads=[], delete=False):
        """
        List and optionally discard uploads that are in the assetstore but not
        in the known list.
        :param knownUploads: a list of upload dictionaries of all known
                             incomplete uploads.
        :type knownUploads: list
        :param delete: if True, delete any unknown uploads.
        :type delete: bool
        :returns: a list of unknown uploads.
        """
        untrackedList = []
        prefix = self.assetstore.get('prefix', '')
        if prefix:
            prefix += '/'
        conn = botoConnectS3(self.assetstore.get('botoConnect', {}))
        bucket = conn.lookup(bucket_name=self.assetstore['bucket'],
                             validate=True)
        if not bucket:
            return []
        getParams = {}
        while True:
            try:
                multipartUploads = bucket.get_all_multipart_uploads(**getParams)
            except boto.exception.S3ResponseError:
                break
            if not len(multipartUploads):
                break
            for multipartUpload in multipartUploads:
                if self._uploadIsKnown(multipartUpload, knownUploads):
                    continue
                # don't include uploads with a different prefix; this allows a
                # single bucket to handle multiple assetstores and us to only
                # clean up the one we are in.  We could further validate that
                # the key name was of the format /(prefix)/../../(id)
                if not multipartUpload.key_name.startswith(prefix):
                    continue
                unknown = {'s3': {'uploadId': multipartUpload.id,
                                  'key': multipartUpload.key_name}}
                untrackedList.append(unknown)
                if delete:
                    multipartUpload.cancel_upload()
            if not multipartUploads.is_truncated:
                break
            getParams['key_marker'] = multipartUploads.next_key_marker
            getParams['upload_id_marker'] = \
                multipartUploads.next_upload_id_marker
        return untrackedList

    def _uploadIsKnown(self, multipartUpload, knownUploads):
        """
        Check if a multipartUpload as returned by boto is in our list of known
        uploads.
        :param multipartUpload: an upload entry from get_all_multipart_uploads.
        :param knownUploads: a list of our known uploads.
        :results: TRue if the upload is known.
        """
        for upload in knownUploads:
            if ('s3' in upload and 'uploadId' in upload['s3'] and
                    'key' in upload['s3']):
                if (multipartUpload.id == upload['s3']['uploadId'] and
                        multipartUpload.key_name == upload['s3']['key']):
                    return True
        return False

    def _botoGenerateUrl(self, key, method='GET', headers=None,
                         queryParams=None):
        """
        Generate a URL to communicate with the S3 server.  This leverages the
        boto generate_url method, but has additional parameters to compensate
        for that methods lack of exposing query parameters.
        :param method: one of 'GET', 'PUT', 'POST', or 'DELETE'.
        :param key: the name of the S3 key to use.
        :param headers: if present, a dictionary of headers to encode in the
                        request.
        :param queryParams: if present, parameters to add to the query.
        :returns: a url that can be sent with the headers to the S3 server.
        """
        conn = botoConnectS3(self.assetstore.get('botoConnect', {}))
        if queryParams:
            keyquery = key+'?'+queryParams
        else:
            keyquery = key
        url = conn.generate_url(
            expires_in=self.HMAC_TTL, method=method,
            bucket=self.assetstore['bucket'], key=keyquery, headers=headers)
        if queryParams:
            parts = url.split('?')
            if len(parts) == 3:
                config = self.assetstore.get('botoConnect', {})
                # This clause allows use to work with a moto server.  It will
                # probably do no harm in any real scenario
                if (queryParams == "uploads" and
                        not config.get('is_secure', True) and
                        config.get('host') == '127.0.0.1'):
                    url = parts[0]+'?'+parts[1]
                else:
                    url = parts[0]+'?'+parts[1]+'&'+parts[2]
        return url


class BotoCallingFormat(boto.s3.connection.OrdinaryCallingFormat):
    # By subclassing boto's calling format, we can pass upload parameters along
    # with the key and get it to do the work of creating urls for us.  The only
    # difference between boto's OrdinaryCallingFormat and this is that we don't
    # urllib.quote the key
    def build_auth_path(self, bucket, key=''):
        key = boto.utils.get_utf8_value(key)
        path = ''
        if bucket != '':
            path = '/' + bucket
        return path + '/%s' % key

    def build_path_base(self, bucket, key=''):
        key = boto.utils.get_utf8_value(key)
        path_base = '/'
        if bucket:
            path_base += "%s/" % bucket
        return path_base + key


def botoConnectS3(connectParams):
    """
    Connect to the S3 server, throwing an appropriate exception if we fail.
    :param connectParams: a dictionary of paramters to use in the connection.
    :returns: the boto connection object.
    """
    try:
        conn = boto.connect_s3(calling_format=BotoCallingFormat(),
                               **connectParams)
    except Exception:
        logger.exception('S3 assetstore validation exception')
        raise ValidationException('Unable to connect to S3 assetstore')
    return conn


def makeBotoConnectParams(accessKeyId, secret, service=None):
    """
    Create a dictionary of values to pass to the boto connect_s3 function.
    :param accessKeyId: the S3 access key ID
    :param secret: the S3 secret key
    :param service: the name of the service in the form
                    [http[s]://](host domain)[:(port)].
    :returns: boto connection parameter dictionary.
    """
    connect = {
        'aws_access_key_id': accessKeyId,
        'aws_secret_access_key': secret,
        }
    if service:
        service = re.match("^((https?)://)?([^:/]+)(:([0-9]+))?$", service)
        if service.groups()[1] == 'http':
            connect['is_secure'] = False
        connect['host'] = service.groups()[2]
        if service.groups()[4] is not None:
            connect['port'] = int(service.groups()[4])
    return connect


def _deleteFileImpl(event):
    """
    Uses boto to delete the key.
    """
    info = event.info
    conn = botoConnectS3(info.get('botoConnect', {}))
    bucket = conn.lookup(bucket_name=info['bucket'], validate=False)
    key = bucket.get_key(info['key'], validate=True)
    if key:
        bucket.delete_key(key)


events.bind('_s3_assetstore_delete_file', '_s3_assetstore_delete_file',
            _deleteFileImpl)
