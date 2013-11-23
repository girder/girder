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
import os
import pymongo

from .docs import file_docs
from ..rest import Resource, RestException
from ...constants import AccessType
from girder.models.model_base import AccessException


class File(Resource):
    """
    API Endpoint for files. Includes utilities for uploading and downloading
    them.
    """
    def initUpload(self, user, params):
        """
        Before any bytes of the actual file are sent, a request should be made
        to initialize the upload. This creates the temporary record of the
        forthcoming upload that will be passed in chunks to the readChunk
        method.
        """
        self.requireParams(['name', 'parentId', 'parentType', 'size'], params)

        parentType = params['parentType'].lower()

        if parentType == 'folder':
            parent = self.getObjectById(
                self.model('folder'), id=params['parentId'],
                checkAccess=True, user=user, level=AccessType.WRITE)
        elif parentType == 'item':
            parent = self.getObjectById(
                self.model('item'), id=params['parentId'])
            # Ensure write access into parent folder
            self.getObjectById(
                self.model('folder'), user=user, id=parent['folderId'],
                checkAccess=True, level=AccessType.WRITE)
        else:
            raise RestException('Set parentType to item or folder.')

        upload = self.model('upload').createUpload(
            user=user, name=params['name'], parentType=parentType,
            parent=parent, size=int(params['size']))
        if upload['size'] > 0:
            return upload
        else:
            return self.model('upload').finalizeUpload(upload)

    def requestOffset(self, user, params):
        """
        This should be called when resuming an interrupted upload. It will
        report the offset into the upload that should be used to resume.
        :param uploadId: The _id of the temp upload record being resumed.
        :returns: The offset in bytes that the client should use.
        """
        self.requireParams(['uploadId'], params)
        upload = self.getObjectById(self.model('upload'), id=params['uploadId'])
        offset = self.model('upload').requestOffset(upload)
        upload['received'] = offset
        self.model('upload').save(upload)

        return {'offset': offset}

    def readChunk(self, user, params):
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
        self.requireParams(['offset', 'uploadId', 'chunk'], params)

        upload = self.getObjectById(self.model('upload'), id=params['uploadId'])
        offset = int(params['offset'])

        if upload['userId'] != user['_id']:
            raise AccessException('You did not initiate this upload.')

        if upload['received'] != offset:
            raise RestException(
                'Server has received %s bytes, but client sent offset %s.'
                % (upload['received'], offset))

        return self.model('upload').handleChunk(upload, params['chunk'].file)

    def download(self, user, params, fileId):
        """
        Defers to the underlying assetstore adapter to stream a file out.
        Requires read permission on the folder that contains the file's item.
        """
        offset = int(params.get('offset', 0))

        file = self.getObjectById(self.model('file'), id=fileId)
        item = self.getObjectById(self.model('item'), id=file['itemId'])
        self.getObjectById(self.model('folder'), id=item['folderId'],
                           checkAccess=True, user=user)
        return self.model('file').download(file, offset)

    @Resource.endpoint
    def GET(self, path, params):
        user = self.getCurrentUser()

        if not path:
            raise RestException('Invalid path format for GET request')
        elif path[0] == 'offset':
            return self.requestOffset(user, params)
        elif len(path) == 1:  # Assume it's an id
            pass  # TODO get by id
        elif path[1] == 'download':
            return self.download(user, params=params, fileId=path[0])

    @Resource.endpoint
    def POST(self, path, params):
        """
        Use this endpoint to upload a new file.
        """
        user = self.getCurrentUser()

        if not user:
            raise AccessException('Must be logged in to upload.')

        if not path:  # POST /file/ means init new upload
            return self.initUpload(user, params)
        elif path[0] == 'chunk':  # POST /file/chunk means uploading a chunk
            return self.readChunk(user, params)
        else:
            raise RestException('Invalid path format for POST request')

    @Resource.endpoint
    def DELETE(self, path, params):
        """
        Use this endpoint to delete files.
        """
        user = self.getCurrentUser()

        if not path:
            raise RestException('Invalid path format for DELETE request')

        file = self.getObjectById(self.model('file'), id=path[0])
        item = self.getObjectById(self.model('item'), id=file['itemId'])
        self.getObjectById(
            self.model('folder'), id=item['folderId'], user=user,
            checkAccess=True, level=AccessType.ADMIN)

        self.model('file').remove(file)
