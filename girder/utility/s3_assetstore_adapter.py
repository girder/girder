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

import boto3
import botocore
import cherrypy
import json
import re
import requests
import six
import uuid

from girder import logger, events
from girder.models.model_base import GirderException, ValidationException
from .abstract_assetstore_adapter import AbstractAssetstoreAdapter

BUF_LEN = 65536  # Buffer size for download stream


class S3AssetstoreAdapter(AbstractAssetstoreAdapter):
    """
    This assetstore type stores files on S3. It is responsible for generating
    HMAC-signed messages that authorize the client to communicate directly with
    the S3 server where the files are stored.
    """

    CHUNK_LEN = 1024 * 1024 * 32  # Chunk size for uploading
    HMAC_TTL = 120  # Number of seconds each signed message is valid

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

        # construct a set of connection parameters based on the keys and the service
        if 'service' not in doc:
            doc['service'] = ''
        if doc['service'] != '':
            if not re.match('^((https?)://)?([^:/]+)(:([0-9]+))?$', doc['service']):
                raise ValidationException(
                    'The service must of the form [http[s]://](host domain)[:(port)].', 'service')
        params = makeBotoConnectParams(doc['accessKeyId'], doc['secret'], doc['service'])
        conn = botoResource(params)
        if doc.get('readOnly'):
            # TODO(zach) readonly support
            try:
                conn.get_bucket(bucket_name=doc['bucket'], validate=True)
            except Exception:
                logger.exception('S3 assetstore validation exception')
                raise ValidationException(
                    'Unable to connect to bucket "%s".' % doc['bucket'], 'bucket')
        else:
            # Make sure we can write into the given bucket using boto
            try:
                testKey = conn.Object(
                    bucket_name=doc['bucket'], key='/'.join(filter(None, (doc['prefix'], 'test'))))
                testKey.put(Body=b'')
                testKey.delete()
            except Exception:
                logger.exception('S3 assetstore validation exception')
                raise ValidationException(
                    'Unable to write into bucket "%s".' % doc['bucket'], 'bucket')

        return doc

    def __init__(self, assetstore):
        """
        :param assetstore: The assetstore to act on.
        """
        super(S3AssetstoreAdapter, self).__init__(assetstore)
        if all(k in self.assetstore for k in ('accessKeyId', 'secret', 'service')):
            self.connectParams = makeBotoConnectParams(
                self.assetstore['accessKeyId'], self.assetstore['secret'],
                self.assetstore['service'])

    def _getRequestHeaders(self, upload):
        return {
            'Content-Disposition': 'attachment; filename="%s"' % upload['name'],
            'Content-Type': upload.get('mimeType', ''),
            'x-amz-acl': 'private',
            'x-amz-meta-uploader-id': str(upload['userId']),
            'x-amz-meta-uploader-ip': str(cherrypy.request.remote.ip)
        }

    def initUpload(self, upload):
        """
        Build the request required to initiate an authorized upload to S3.
        """
        if upload['size'] <= 0:
            return upload

        # collapse consecutive spaces in the filename into a single space
        # this is due to a bug in S3 that does not properly handle filenames
        # with multiple spaces in a row, resulting in a SignatureDoesNotMatch error
        # TODO(zach) test multiple consecutive spaces in filename
        # upload['name'] = re.sub('\s+', ' ', upload['name'])

        uid = uuid.uuid4().hex
        key = '/'.join(filter(
            None, (self.assetstore.get('prefix', ''), uid[:2], uid[2:4], uid)))
        path = '/%s/%s' % (self.assetstore['bucket'], key)

        chunked = upload['size'] > self.CHUNK_LEN

        upload['behavior'] = 's3'
        upload['s3'] = {
            'chunked': chunked,
            'chunkLength': self.CHUNK_LEN,
            'relpath': path,
            'key': key
        }

        conn = botoClient(self.connectParams)

        if chunked:
            # TODO chunked
            upload['s3']['request'] = {'method': 'POST'}
            alsoSignHeaders = {}
            queryParams = {'uploads': None}
        else:
            headers = self._getRequestHeaders(upload)
            url = conn.generate_presigned_url(
                ClientMethod='put_object', Params={
                    'Bucket': self.assetstore['bucket'],
                    'Key': key,
                    'ACL': headers['x-amz-acl'],
                    'ContentLength': upload['size'],
                    'ContentDisposition': headers['Content-Disposition'],
                    'ContentType': headers['Content-Type'],
                    'Metadata': {
                        'uploader-id': headers['x-amz-meta-uploader-id'],
                        'uploader-ip': headers['x-amz-meta-uploader-ip']
                    }
                })
            upload['s3']['request'] = {
                'method': 'PUT',
                'url': url,
                'headers': headers
            }

        return upload

    def uploadChunk(self, upload, chunk):
        """
        Rather than processing actual bytes of the chunk, this will generate
        the signature required to upload the chunk. Clients that do not support
        direct-to-S3 upload can pass the chunk via the request body as with
        other assetstores, and Girder will proxy the data through to S3.

        :param chunk: This should be a JSON string containing the chunk number
            and S3 upload ID. If a normal chunk file-like object is passed,
            we will send the data to S3.
        """
        if isinstance(chunk, six.string_types):
            return self._clientUploadChunk(upload, chunk)
        else:
            return self._proxiedUploadChunk(upload, chunk)

    def _clientUploadChunk(self, upload, chunk):
        """
        Clients that support direct-to-S3 upload behavior will go through this
        method by sending a normally-encoded form string as the chunk parameter,
        containing the required JSON info for uploading. This generates the
        signed URL that the client should use to upload the chunk to S3.
        """
        info = json.loads(chunk)
        index = int(info['partNumber']) - 1
        length = min(self.CHUNK_LEN, upload['size'] - index * self.CHUNK_LEN)

        if 'contentLength' in info and int(info['contentLength']) != length:
            raise ValidationException('Expected chunk size %d, but got %d.' % (
                length, info['contentLength']))

        if length <= 0:
            raise ValidationException('Invalid chunk length %d.' % length)

        queryParams = {
            'partNumber': info['partNumber'],
            'uploadId': info['s3UploadId']
        }

        url = self._botoGenerateUrl(
            method='PUT', key=upload['s3']['key'], queryParams=queryParams,
            headers={
                'Content-Length': length
            })

        upload['s3']['uploadId'] = info['s3UploadId']
        upload['s3']['partNumber'] = info['partNumber']
        upload['s3']['request'] = {
            'method': 'PUT',
            'url': url
        }

        return upload

    def _getBucket(self, validate=True):
        conn = botoResource(self.assetstore['botoConnect'])
        bucket = conn.lookup(bucket_name=self.assetstore['bucket'], validate=validate)

        if not bucket:
            raise Exception('Could not connect to S3 bucket.')

        return bucket

    def _proxiedUploadChunk(self, upload, chunk):
        """
        Clients that do not support direct-to-S3 upload behavior will go through
        this method by sending the chunk data as they normally would for other
        assetstore types. Girder will send the data to S3 on behalf of the client.
        """
        bucket = self._getBucket()

        if upload['s3']['chunked']:
            if 'uploadId' not in upload['s3']:
                # Initiate a new multipart upload
                mp = bucket.initiate_multipart_upload(
                    upload['s3']['key'],
                    headers=self._getRequestHeaders(upload))
                upload['s3']['uploadId'] = mp.id
                upload['s3']['keyName'] = mp.key_name
                upload['s3']['partNumber'] = 0

            upload['s3']['partNumber'] += 1

            s3Info = upload['s3']
            size = chunk.getSize()

            queryParams = {
                'partNumber': s3Info['partNumber'],
                'uploadId': s3Info['uploadId']
            }
            headers = {
                'Content-Length': str(size)
            }

            url = self._botoGenerateUrl(
                method='PUT', key=s3Info['key'], queryParams=queryParams, headers=headers)

            resp = requests.request(method='PUT', url=url, data=chunk, headers=headers)
            if resp.status_code not in (200, 201):
                logger.error('S3 multipart upload failure %d (uploadId=%s):\n%s' % (
                    resp.status_code, upload['_id'], resp.text))
                raise GirderException('Upload failed (bad gateway)')

            upload['received'] += size
        else:
            size = chunk.getSize()
            if size < upload['size']:
                raise ValidationException('Uploads of this length must be sent in a single chunk.')

            reqInfo = upload['s3']['request']
            resp = requests.request(
                method=reqInfo['method'], url=reqInfo['url'], data=chunk,
                headers=dict(reqInfo['headers'], **{'Content-Length': str(size)}))
            if resp.status_code not in (200, 201):
                logger.error('S3 upload failure %d (uploadId=%s):\n%s' % (
                    resp.status_code, upload['_id'], resp.text))
                raise GirderException('Upload failed (bad gateway)')

            upload['received'] = size

        return upload

    def requestOffset(self, upload):
        if upload['received'] > 0:
            # This is only set when we are proxying the data to S3
            return upload['received']

        if upload['s3']['chunked']:
            raise ValidationException(
                'You should not call requestOffset on a chunked direct-to-S3 '
                'upload.')

        headers = self._getRequestHeaders(upload)
        url = self._botoGenerateUrl(method='PUT', key=upload['s3']['key'],
                                    headers=headers)
        return {
            'method': 'PUT',
            'url': url,
            'headers': headers,
            'offset': 0
        }

    def finalizeUpload(self, upload, file):
        if upload['size'] <= 0:
            return file

        file['relpath'] = upload['s3']['relpath']
        file['s3Key'] = upload['s3']['key']

        if upload['s3']['chunked']:
            if upload['received'] > 0:
                # We proxied the data to S3
                bucket = self._getBucket()
                mp = boto.s3.multipart.MultiPartUpload(bucket)
                mp.id = upload['s3']['uploadId']
                mp.key_name = upload['s3']['keyName']
                mp.complete_upload()
            else:
                queryParams = {'uploadId': upload['s3']['uploadId']}
                headers = {'Content-Type': 'text/plain;charset=UTF-8'}
                url = self._botoGenerateUrl(
                    method='POST', key=upload['s3']['key'], headers=headers,
                    queryParams=queryParams)
                file['s3FinalizeRequest'] = {
                    'method': 'POST',
                    'url': url,
                    'headers': headers
                }
                file['additionalFinalizeKeys'] = ('s3FinalizeRequest',)
        return file

    def downloadFile(self, file, offset=0, headers=True, endByte=None,
                     contentDisposition=None, extraParameters=None, **kwargs):
        """
        When downloading a single file with HTTP, we redirect to S3. Otherwise,
        e.g. when downloading as part of a zip stream, we connect to S3 and
        pipe the bytes from S3 through the server to the user agent.
        """
        if headers:
            if file['size'] > 0:
                params = {
                    'Bucket': self.assetstore['bucket'],
                    'Key': file['s3Key']
                }
                if contentDisposition == 'inline':
                    params['ResponseContentDisposition'] = 'inline; filename="%s"' % file['name']
                url = botoClient(self.connectParams).generate_presigned_url(
                    ClientMethod='get_object', Params=params)
                raise cherrypy.HTTPRedirect(url)
            else:
                self.setContentHeaders(file, 0, 0)

                def stream():
                    yield ''
                return stream
        else:
            def stream():
                if file['size'] > 0:
                    pipe = requests.get(urlFn(key=file['s3Key']), stream=True)
                    for chunk in pipe.iter_content(chunk_size=BUF_LEN):
                        if chunk:
                            yield chunk
                else:
                    yield ''
            return stream

    def importData(self, parent, parentType, params, progress, user, bucket=None, **kwargs):
        importPath = params.get('importPath', '').strip().lstrip('/')

        if importPath and not importPath.endswith('/'):
            importPath += '/'

        if bucket is None:
            bucket = self._getBucket()

        for obj in bucket.list(importPath, '/'):
            if progress:
                progress.update(message=obj.name)

            if isinstance(obj, boto.s3.prefix.Prefix):
                name = obj.name.rstrip('/').rsplit('/', 1)[-1]
                folder = self.model('folder').createFolder(
                    parent=parent, name=name, parentType=parentType,
                    creator=user, reuseExisting=True)
                self.importData(parent=folder, parentType='folder', params={
                    'importPath': obj.name
                }, progress=progress, user=user, bucket=bucket, **kwargs)
            elif isinstance(obj, boto.s3.key.Key):
                name = obj.name.rsplit('/', 1)[-1]
                if not name:
                    continue

                if parentType != 'folder':
                    raise ValidationException(
                        'Keys cannot be imported directly underneath a %s.' % parentType)

                if self.shouldImportFile(obj.name, params):
                    item = self.model('item').createItem(
                        name=name, creator=user, folder=parent, reuseExisting=True)
                    file = self.model('file').createFile(
                        name=name, creator=user, item=item, reuseExisting=True,
                        assetstore=self.assetstore, mimeType=None, size=obj.size)
                    file['s3Key'] = obj.name
                    file['imported'] = True
                    self.model('file').save(file)

    def deleteFile(self, file):
        """
        We want to queue up files to be deleted asynchronously since it requires
        an external HTTP request per file in order to delete them, and we don't
        want to wait on that.

        Files that were imported as pre-existing data will not actually be
        deleted from S3, only their references in Girder will be deleted.
        """
        if file['size'] > 0 and 'relpath' in file:
            q = {
                'relpath': file['relpath'],
                'assetstoreId': self.assetstore['_id']
            }
            matching = self.model('file').find(q, limit=2, fields=[])
            if matching.count(True) == 1:
                events.daemon.trigger('_s3_assetstore_delete_file', {
                    'botoConnect': self.assetstore.get('botoConnect', {}),
                    'bucket': self.assetstore['bucket'],
                    'key': file['s3Key']
                })

    def fileUpdated(self, file):
        """
        On file update, if the name or the MIME type changed, we must update
        them accordingly on the S3 key so that the file downloads with the
        correct name and content type.
        """
        # TODO(zach) update file mimetype
        if file.get('imported'):
            return

        bucket = self._getBucket()
        key = bucket.get_key(file['s3Key'], validate=True)

        if not key:
            return

        disp = 'attachment; filename="%s"' % file['name']
        mime = file.get('mimeType') or ''

        if key.content_type != mime or key.content_disposition != disp:
            key.set_remote_metadata(metadata_plus={
                'Content-Type': mime,
                'Content-Disposition': disp.encode('utf8')
            }, metadata_minus=[], preserve_acl=True)

    def cancelUpload(self, upload):
        """
        Delete the temporary files associated with a given upload.
        """
        if 's3' not in upload:
            return
        if 'key' not in upload['s3']:
            return

        bucket = self._getBucket()
        if bucket:
            key = bucket.get_key(upload['s3']['key'], validate=True)
            if key:
                bucket.delete_key(key)
            # check if this is an abandoned multipart upload
            if 's3' in upload and 'uploadId' in upload['s3'] and 'key' in upload['s3']:
                getParams = {}
                while True:
                    try:
                        multipartUploads = bucket.get_all_multipart_uploads(**getParams)
                    except boto.exception.S3ResponseError:
                        break
                    if not len(multipartUploads):
                        break
                    for multipartUpload in multipartUploads:
                        if (multipartUpload.id == upload['s3']['uploadId'] and
                                multipartUpload.key_name == upload['s3']['key']):
                            multipartUpload.cancel_upload()
                    if not multipartUploads.is_truncated:
                        break
                    getParams['key_marker'] = multipartUploads.next_key_marker
                    getParams['upload_id_marker'] = multipartUploads.next_upload_id_marker

    def untrackedUploads(self, knownUploads=None, delete=False):
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
        if self.assetstore.get('readOnly'):
            return []

        untrackedList = []
        prefix = self.assetstore.get('prefix', '')
        if prefix:
            prefix += '/'

        if knownUploads is None:
            knownUploads = []

        bucket = self._getBucket()
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
            getParams['upload_id_marker'] = multipartUploads.next_upload_id_marker
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


def botoResource(connectParams):
    """
    Connect to the S3 server, throwing an appropriate exception if we fail.
    :param connectParams: a dictionary of parameters to use in the connection.
    :returns: the boto connection object.
    """
    try:
        return boto3.resource('s3', **connectParams)
    except Exception:
        logger.exception('S3 assetstore validation exception')
        raise ValidationException('Unable to connect to S3 assetstore')

def botoClient(connectParams):
    try:
        return boto3.client('s3', **connectParams)
    except Exception:
        logger.exception('S3 assetstore validation exception')
        raise ValidationException('Unable to connect to S3 assetstore')


def makeBotoConnectParams(accessKeyId, secret, service=None):
    """
    Create a dictionary of values to pass to the boto connect_s3 function.

    :param accessKeyId: the S3 access key ID
    :param secret: the S3 secret key
    :param service: alternate service URL
    :returns: boto connection parameter dictionary.
    """
    accessKeyId = accessKeyId or None
    secret = secret or None
    params = {
        'aws_access_key_id': accessKeyId,
        'aws_secret_access_key': secret,
        'config': botocore.client.Config(
            #s3={'addressing_style': 'path'},  TODO I think this is the default
            signature_version='s3v4'
        )
    }

    if service:
        serviceRe = re.match('^((https?)://)?([^:/]+)(:([0-9]+))?$', service)
        if serviceRe.groups()[1] == 'http':
            params['use_ssl'] = False
        params['endpoint_url'] = service

    # TODO(zach) region parameter? Might not be necessary
    return params


def _deleteFileImpl(event):
    """
    Uses boto to delete the key.
    """
    info = event.info
    conn = botoResource(info.get('botoConnect', {}))
    bucket = conn.lookup(bucket_name=info['bucket'], validate=False)
    key = bucket.get_key(info['key'], validate=True)
    if key:
        bucket.delete_key(key)


events.bind('_s3_assetstore_delete_file', '_s3_assetstore_delete_file',
            _deleteFileImpl)
