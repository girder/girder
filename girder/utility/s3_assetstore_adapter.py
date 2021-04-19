# -*- coding: utf-8 -*-
import datetime
import json
import re
import urllib.parse
import uuid

import boto3
import botocore
import cherrypy
import requests

from girder import events, logger
from girder.api.rest import setContentDisposition
from girder.exceptions import GirderException, ValidationException
from girder.models.file import File
from girder.models.folder import Folder
from girder.models.item import Item

from .abstract_assetstore_adapter import AbstractAssetstoreAdapter

BUF_LEN = 65536  # Buffer size for download stream
DEFAULT_REGION = 'us-east-1'


class S3AssetstoreAdapter(AbstractAssetstoreAdapter):
    """
    This assetstore type stores files on S3. It is responsible for generating
    HMAC-signed messages that authorize the client to communicate directly with
    the S3 server where the files are stored.
    """

    CHUNK_LEN = 1024 * 1024 * 32  # Chunk size for uploading
    HMAC_TTL = 120  # Number of seconds each signed message is valid

    @staticmethod
    def _s3Client(connectParams):
        try:
            client = boto3.client('s3', **connectParams)
            if 'googleapis' in urllib.parse.urlparse(connectParams.get(
                    'endpoint_url', '')).netloc.split('.'):
                client.meta.events.unregister(
                    'before-parameter-build.s3.ListObjects',
                    botocore.handlers.set_list_objects_encoding_type_url)
                client._useGoogleAccessId = True
            return client
        except Exception:
            logger.exception('S3 assetstore validation exception')
            raise ValidationException('Unable to connect to S3 assetstore')

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
        params = makeBotoConnectParams(
            doc['accessKeyId'], doc['secret'], doc['service'], doc.get('region'),
            doc.get('inferCredentials'))
        client = S3AssetstoreAdapter._s3Client(params)
        if doc.get('readOnly'):
            try:
                client.head_bucket(Bucket=doc['bucket'])
            except Exception:
                logger.exception('S3 assetstore validation exception')
                raise ValidationException(
                    'Unable to connect to bucket "%s".' % doc['bucket'], 'bucket')
        else:
            # Make sure we can write into the given bucket using boto
            try:
                key = '/'.join(filter(None, (doc['prefix'], 'girder_test')))
                client.put_object(Bucket=doc['bucket'], Key=key, Body=b'')
                client.delete_object(Bucket=doc['bucket'], Key=key)
            except Exception:
                logger.exception('S3 assetstore validation exception')
                raise ValidationException(
                    'Unable to write into bucket "%s".' % doc['bucket'], 'bucket')

        return doc

    def __init__(self, assetstore):
        super().__init__(assetstore)
        if all(k in self.assetstore for k in ('accessKeyId', 'secret', 'service')):
            self.connectParams = makeBotoConnectParams(
                self.assetstore['accessKeyId'], self.assetstore['secret'],
                self.assetstore['service'], self.assetstore.get('region'),
                self.assetstore.get('inferCredentials'))
            self.client = S3AssetstoreAdapter._s3Client(self.connectParams)

    def _getRequestHeaders(self, upload):
        headers = {
            'Content-Disposition': setContentDisposition(upload['name'], setHeader=False),
            'Content-Type': upload.get('mimeType', ''),
            'x-amz-acl': 'private',
            'x-amz-meta-uploader-id': str(upload['userId']),
            'x-amz-meta-uploader-ip': str(cherrypy.request.remote.ip)
        }
        if self.assetstore.get('serverSideEncryption'):
            headers['x-amz-server-side-encryption'] = 'AES256'

        return headers

    def _generatePresignedUrl(self, *args, **kwargs):
        """
        Wrap self.client.generate_presigned_url to allow it work with
        Google Cloud Storage.

        See https://gist.github.com/gleicon/2b8acb9f9c0f22753eaac227ff997b34
        """
        url = self.client.generate_presigned_url(*args, **kwargs)
        if getattr(self.client, '_useGoogleAccessId', False):
            awskey, gskey = 'AWSAccessKeyId', 'GoogleAccessId'
            parsed = urllib.parse.urlparse(url)
            if awskey in urllib.parse.parse_qs(parsed.query):
                qsl = urllib.parse.parse_qsl(parsed.query)
                qsl = [(key if key != awskey else gskey, value) for key, value in qsl]
                url = urllib.parse.urlunparse((
                    parsed[0], parsed[1], parsed[2], parsed[3],
                    urllib.parse.urlencode(qsl),
                    parsed[5]))
        return url

    def initUpload(self, upload):
        """
        Build the request required to initiate an authorized upload to S3.
        """
        if upload['size'] <= 0:
            return upload

        uid = uuid.uuid4().hex
        key = '/'.join(filter(
            None, (self.assetstore.get('prefix', ''), uid[:2], uid[2:4], uid)))
        path = '/%s/%s' % (self.assetstore['bucket'], key)
        chunked = upload['size'] > self.CHUNK_LEN
        headers = self._getRequestHeaders(upload)
        params = {
            'Bucket': self.assetstore['bucket'],
            'Key': key,
            'ACL': headers['x-amz-acl'],
            'ContentDisposition': headers['Content-Disposition'],
            'ContentType': headers['Content-Type'],
            'Metadata': {
                'uploader-id': headers['x-amz-meta-uploader-id'],
                'uploader-ip': headers['x-amz-meta-uploader-ip']
            }
        }

        if self.assetstore.get('serverSideEncryption'):
            params['ServerSideEncryption'] = 'AES256'

        requestInfo = {
            'headers': headers,
            'method': 'PUT'
        }
        upload['behavior'] = 's3'
        upload['s3'] = {
            'chunked': chunked,
            'chunkLength': self.CHUNK_LEN,
            'relpath': path,
            'key': key,
            'request': requestInfo
        }

        if chunked:
            method = 'create_multipart_upload'
            requestInfo['method'] = 'POST'
        else:
            method = 'put_object'
            params['ContentLength'] = upload['size']

        requestInfo['url'] = self._generatePresignedUrl(ClientMethod=method, Params=params)
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
        if isinstance(chunk, str):
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

        url = self._generatePresignedUrl(ClientMethod='upload_part', Params={
            'Bucket': self.assetstore['bucket'],
            'Key': upload['s3']['key'],
            'ContentLength': length,
            'UploadId': info['s3UploadId'],
            'PartNumber': info['partNumber']
        })

        upload['s3']['uploadId'] = info['s3UploadId']
        upload['s3']['partNumber'] = info['partNumber']
        upload['s3']['request'] = {
            'method': 'PUT',
            'url': url
        }

        return upload

    def _proxiedUploadChunk(self, upload, chunk):
        """
        Clients that do not support direct-to-S3 upload behavior will go through
        this method by sending the chunk data as they normally would for other
        assetstore types. Girder will send the data to S3 on behalf of the client.
        """
        if upload['s3']['chunked']:
            if 'uploadId' not in upload['s3']:
                # Initiate a new multipart upload if this is the first chunk
                disp = 'attachment; filename="%s"' % upload['name']
                mime = upload.get('mimeType', '')
                mp = self.client.create_multipart_upload(
                    Bucket=self.assetstore['bucket'], Key=upload['s3']['key'],
                    ACL='private', ContentDisposition=disp, ContentType=mime,
                    Metadata={
                        'uploader-id': str(upload['userId']),
                        'uploader-ip': str(cherrypy.request.remote.ip)
                    })
                upload['s3']['uploadId'] = mp['UploadId']
                upload['s3']['keyName'] = mp['Key']
                upload['s3']['partNumber'] = 0

            upload['s3']['partNumber'] += 1
            size = chunk.getSize()
            headers = {
                'Content-Length': str(size)
            }

            # We can't just call upload_part directly because they require a
            # seekable file object, and ours isn't.
            url = self._generatePresignedUrl(ClientMethod='upload_part', Params={
                'Bucket': self.assetstore['bucket'],
                'Key': upload['s3']['key'],
                'ContentLength': size,
                'UploadId': upload['s3']['uploadId'],
                'PartNumber': upload['s3']['partNumber']
            })

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
                'You should not call requestOffset on a chunked direct-to-S3 upload.')

        headers = self._getRequestHeaders(upload)
        params = {
            'Bucket': self.assetstore['bucket'],
            'Key': upload['s3']['key'],
            'ACL': headers['x-amz-acl'],
            'ContentDisposition': headers['Content-Disposition'],
            'ContentLength': upload['size'],
            'ContentType': headers['Content-Type'],
            'Metadata': {
                'uploader-id': headers['x-amz-meta-uploader-id'],
                'uploader-ip': headers['x-amz-meta-uploader-ip']
            }
        }

        if self.assetstore.get('serverSideEncryption'):
            params['ServerSideEncryption'] = 'AES256'

        url = self._generatePresignedUrl(ClientMethod='put_object', Params=params)

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
                parts = self.client.list_parts(
                    Bucket=self.assetstore['bucket'], Key=file['s3Key'],
                    UploadId=upload['s3']['uploadId'])
                parts = [{
                    'ETag': part['ETag'],
                    'PartNumber': part['PartNumber']
                } for part in parts.get('Parts', [])]
                self.client.complete_multipart_upload(
                    Bucket=self.assetstore['bucket'], Key=file['s3Key'],
                    UploadId=upload['s3']['uploadId'], MultipartUpload={'Parts': parts})
            else:
                url = self._generatePresignedUrl(
                    ClientMethod='complete_multipart_upload', Params={
                        'Bucket': self.assetstore['bucket'],
                        'Key': upload['s3']['key'],
                        'UploadId': upload['s3']['uploadId']
                    })
                file['s3FinalizeRequest'] = {
                    'method': 'POST',
                    'url': url,
                    'headers': {'Content-Type': 'text/plain;charset=UTF-8'}
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
        if file['size'] <= 0:
            if headers:
                self.setContentHeaders(file, 0, 0)

            def stream():
                yield ''
            return stream

        params = {
            'Bucket': self.assetstore['bucket'],
            'Key': file['s3Key']
        }

        if contentDisposition == 'inline' and not file.get('imported'):
            params['ResponseContentDisposition'] = 'inline; filename="%s"' % file['name']

        url = self._generatePresignedUrl(ClientMethod='get_object', Params=params)

        if headers:
            raise cherrypy.HTTPRedirect(url)
        else:
            headers = {}
            if offset or endByte is not None:
                if endByte is None or endByte > file['size']:
                    endByte = file['size']
                headers = {'Range': 'bytes=%d-%d' % (offset, endByte - 1)}

            def stream():
                pipe = requests.get(url, stream=True, headers=headers)
                for chunk in pipe.iter_content(chunk_size=BUF_LEN):
                    if chunk:
                        yield chunk
            return stream

    def importData(self, parent, parentType, params, progress,
                   user, force_recursive=True, **kwargs):
        importPath = params.get('importPath', '').strip().lstrip('/')
        bucket = self.assetstore['bucket']
        now = datetime.datetime.utcnow()
        paginator = self.client.get_paginator('list_objects')
        pageIterator = paginator.paginate(Bucket=bucket, Prefix=importPath, Delimiter='/')
        for resp in pageIterator:
            # Start with objects
            for obj in resp.get('Contents', []):
                if progress:
                    progress.update(message=obj['Key'])

                name = obj['Key'].rsplit('/', 1)[-1]
                if not name:
                    continue

                if parentType != 'folder':
                    raise ValidationException(
                        'Keys cannot be imported directly underneath a %s.' % parentType)

                if self.shouldImportFile(obj['Key'], params):
                    item = Item().createItem(
                        name=name, creator=user, folder=parent, reuseExisting=True)
                    events.trigger('s3_assetstore_imported', {
                        'id': item['_id'],
                        'type': 'item',
                        'importPath': obj['Key'],
                    })
                    # Create a file record; delay saving it until we have added
                    # the import information.
                    file = File().createFile(
                        name=name, creator=user, item=item, reuseExisting=True,
                        assetstore=self.assetstore, mimeType=None, size=obj['Size'],
                        saveFile=False)
                    file['s3Key'] = obj['Key']
                    file['imported'] = True
                    File().save(file)

            for obj in resp.get('CommonPrefixes', []):
                if progress:
                    progress.update(message=obj['Prefix'])

                name = obj['Prefix'].rstrip('/').rsplit('/', 1)[-1]
                folder = Folder().createFolder(
                    parent=parent, name=name, parentType=parentType, creator=user,
                    reuseExisting=True)

                events.trigger('s3_assetstore_imported', {
                    'id': folder['_id'],
                    'type': 'folder',
                    'importPath': obj['Prefix'],
                })
                # recurse into subdirectories if force_recursive is true
                # or the folder was newly created.
                if force_recursive or folder['created'] >= now:
                    self.importData(parent=folder, parentType='folder', params={
                        **params, 'importPath': obj['Prefix']
                    }, progress=progress, user=user, **kwargs)

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
            matching = File().find(q, limit=2, fields=[])
            if matching.count(True) == 1:
                events.daemon.trigger(info={
                    'client': self.client,
                    'bucket': self.assetstore['bucket'],
                    'key': file['s3Key']
                }, callback=_deleteFileImpl)

    def fileUpdated(self, file):
        """
        On file update, if the name or the MIME type changed, we must update
        them accordingly on the S3 key so that the file downloads with the
        correct name and content type.
        """
        if file.get('imported'):
            return

        bucket = self.assetstore['bucket']
        try:
            key = self.client.head_object(Bucket=bucket, Key=file['s3Key'])
        except botocore.exceptions.ClientError:
            return

        disp = 'attachment; filename="%s"' % file['name']
        mime = file.get('mimeType') or ''

        if key.get('ContentType') != mime or key.get('ContentDisposition') != disp:
            self.client.copy_object(
                Bucket=bucket, Key=file['s3Key'], Metadata=key['Metadata'],
                CopySource={'Bucket': bucket, 'Key': file['s3Key']}, ContentDisposition=disp,
                ContentType=mime, MetadataDirective='REPLACE')

    def cancelUpload(self, upload):
        """
        Delete the temporary files associated with a given upload.
        """
        if 'key' not in upload.get('s3', {}):
            return
        bucket = self.assetstore['bucket']
        key = upload['s3']['key']
        self.client.delete_object(Bucket=bucket, Key=key)

        # check if this is an abandoned multipart upload
        if 'uploadId' in upload['s3']:
            try:
                self.client.abort_multipart_upload(
                    Bucket=bucket, Key=key, UploadId=upload['s3']['uploadId'])
            except botocore.exceptions.ClientError:
                pass

    def untrackedUploads(self, knownUploads=None, delete=False):
        """
        List and optionally discard uploads that are in the assetstore but not
        in the known list.

        :param knownUploads: a list of upload dictionaries of all known incomplete uploads.
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

        bucket = self.assetstore['bucket']
        getParams = {'Bucket': bucket}

        while True:
            multipartUploads = self.client.list_multipart_uploads(**getParams)
            if not multipartUploads.get('Uploads'):
                break
            for upload in multipartUploads['Uploads']:
                if self._uploadIsKnown(upload, knownUploads):
                    continue
                # don't include uploads with a different prefix; this allows a
                # single bucket to handle multiple assetstores and us to only
                # clean up the one we are in.  We could further validate that
                # the key name was of the format /(prefix)/../../(id)
                if not upload['Key'].startswith(prefix):
                    continue
                untrackedList.append({
                    's3': {
                        'uploadId': upload['UploadId'],
                        'key': upload['Key'],
                        'created': upload['Initiated']
                    }
                })
                if delete:
                    self.client.abort_multipart_upload(
                        Bucket=bucket, Key=upload['Key'], UploadId=upload['UploadId'])
            if not multipartUploads['IsTruncated']:
                break
            getParams['KeyMarker'] = multipartUploads['NextKeyMarker']
            getParams['UploadIdMarker'] = multipartUploads['NextUploadIdMarker']
        return untrackedList

    def _uploadIsKnown(self, multipartUpload, knownUploads):
        """
        Check if a multipartUpload as returned by boto is in our list of known uploads.

        :param multipartUpload: an upload entry from get_all_multipart_uploads.
        :param knownUploads: a list of our known uploads.
        :results: Whether the upload is known
        """
        for upload in knownUploads:
            if ('s3' in upload and 'uploadId' in upload['s3']
                    and 'key' in upload['s3']):
                if (multipartUpload['UploadId'] == upload['s3']['uploadId']
                        and multipartUpload['Key'] == upload['s3']['key']):
                    return True
        return False


def makeBotoConnectParams(accessKeyId, secret, service=None, region=None, inferCredentials=False):
    """
    Create a dictionary of values to pass to the boto connect_s3 function.

    :param accessKeyId: the S3 access key ID
    :param secret: the S3 secret key
    :param service: alternate service URL
    :param region: the AWS region name of the bucket (if not "us-east-1")
    :param inferCredentials: Whether or not Boto should infer the credentials
        without directly using accessKeyId and secret.
    :returns: boto connection parameter dictionary.
    """
    region = region or DEFAULT_REGION
    if inferCredentials:
        # Look up credentials through Boto's fallback mechanism, see:
        # http://boto3.readthedocs.io/en/latest/guide/configuration.html#configuring-credentials
        params = {
            'config': botocore.client.Config(signature_version='s3v4', region_name=region)
        }
    elif accessKeyId and secret:
        # Use explicitly passed credentials
        params = {
            'aws_access_key_id': accessKeyId,
            'aws_secret_access_key': secret,
            'config': botocore.client.Config(signature_version='s3v4', region_name=region)
        }
    else:
        # Anonymous access
        params = {
            'config': botocore.client.Config(
                signature_version=botocore.UNSIGNED, region_name=region)
        }

    if service:
        if not service.startswith('http://') and not service.startswith('https://'):
            service = 'https://' + service
        params['endpoint_url'] = service

    return params


def _deleteFileImpl(event):
    event.info['client'].delete_object(Bucket=event.info['bucket'], Key=event.info['key'])
