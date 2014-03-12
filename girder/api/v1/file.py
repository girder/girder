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

from .docs import file_docs
from ..rest import Resource, RestException, loadmodel
from ...constants import AccessType
from girder.models.model_base import AccessException


class File(Resource):
    """
    API Endpoint for files. Includes utilities for uploading and downloading
    them.
    """
    def __init__(self):
        self.route('DELETE', (':id',), self.deleteFile)
        self.route('GET', ('offset',), self.requestOffset)
        self.route('GET', (':id', 'download'), self.download)
        self.route('GET', (':id', 'download', ':name'), self.download)
        self.route('POST', (), self.initUpload)
        self.route('POST', ('chunk',), self.readChunk)

    def initUpload(self, params):
        """
        Before any bytes of the actual file are sent, a request should be made
        to initialize the upload. This creates the temporary record of the
        forthcoming upload that will be passed in chunks to the readChunk
        method.
        """
        self.requireParams(('name', 'parentId', 'parentType', 'size'), params)
        user = self.getCurrentUser()

        mimeType = params.get('mimeType', None)
        parentType = params['parentType'].lower()

        if not parentType in ('folder', 'item'):
            raise RestException('The parentType must be "folder" or "item".')

        parent = self.model(parentType).load(id=params['parentId'], user=user,
                                             level=AccessType.WRITE, exc=True)

        upload = self.model('upload').createUpload(
            user=user, name=params['name'], parentType=parentType,
            parent=parent, size=int(params['size']), mimeType=mimeType)
        if upload['size'] > 0:
            return upload
        else:
            return self.model('upload').finalizeUpload(upload)

    def requestOffset(self, params):
        """
        This should be called when resuming an interrupted upload. It will
        report the offset into the upload that should be used to resume.
        :param uploadId: The _id of the temp upload record being resumed.
        :returns: The offset in bytes that the client should use.
        """
        self.requireParams(('uploadId',), params)
        upload = self.model('upload').load(params['uploadId'], exc=True)
        offset = self.model('upload').requestOffset(upload)
        upload['received'] = offset
        self.model('upload').save(upload)

        return {'offset': offset}

    def readChunk(self, params):
        """
        After the temporary upload record has been created (see initUpload),
        the bytes themselves should be passed up in ordered chunks. The user
        must remain logged in when passing each chunk, to authenticate that
        the writer of the chunk is the same as the person who initiated the
        upload. The passed offset is a verification mechanism for ensuring the
        server and client agree on the number of bytes sent/received.
        :param offset: The number of bytes of the file already uploaded prior
                       to this chunk. Should match the server's record of the
                       number of bytes already received.
        :param uploadId: The _id of the temp upload record.
        :param chunk: The blob of data itself.
        """
        self.requireParams(('offset', 'uploadId', 'chunk'), params)
        user = self.getCurrentUser()

        upload = self.model('upload').load(params['uploadId'], exc=True)
        offset = int(params['offset'])

        if upload['userId'] != user['_id']:
            raise AccessException('You did not initiate this upload.')

        if upload['received'] != offset:
            raise RestException(
                'Server has received %s bytes, but client sent offset %s.'
                % (upload['received'], offset))

        return self.model('upload').handleChunk(upload, params['chunk'].file)

    @loadmodel(map={'id': 'file'}, model='file')
    def download(self, file, params, name=None):
        """
        Defers to the underlying assetstore adapter to stream a file out.
        Requires read permission on the folder that contains the file's item.
        """
        offset = int(params.get('offset', 0))
        user = self.getCurrentUser()

        self.model('item').load(id=file['itemId'], user=user,
                                level=AccessType.READ, exc=True)
        return self.model('file').download(file, offset)

    @loadmodel(map={'id': 'file'}, model='file')
    def deleteFile(self, file, params):
        user = self.getCurrentUser()
        self.model('item').load(id=file['itemId'], user=user,
                                level=AccessType.ADMIN, exc=True)
        self.model('file').remove(file)
