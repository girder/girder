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
import errno
import os
import six

from ..describe import Description, autoDescribeRoute, describeRoute
from ..rest import Resource, RestException, filtermodel
from ...constants import AccessType, TokenScope
from girder.models.model_base import AccessException, GirderException
from girder.api import access
from girder.utility import RequestBodyStream
from girder.utility.progress import ProgressContext


class File(Resource):
    """
    API Endpoint for files. Includes utilities for uploading and downloading
    them.
    """
    def __init__(self):
        super(File, self).__init__()
        self.resourceName = 'file'
        self.route('DELETE', (':id',), self.deleteFile)
        self.route('DELETE', ('upload', ':id'), self.cancelUpload)
        self.route('GET', ('offset',), self.requestOffset)
        self.route('GET', (':id',), self.getFile)
        self.route('GET', (':id', 'download'), self.download)
        self.route('GET', (':id', 'download', ':name'), self.downloadWithName)
        self.route('POST', (), self.initUpload)
        self.route('POST', ('chunk',), self.readChunk)
        self.route('POST', ('completion',), self.finalizeUpload)
        self.route('POST', (':id', 'copy'), self.copy)
        self.route('PUT', (':id',), self.updateFile)
        self.route('PUT', (':id', 'contents'), self.updateFileContents)
        self.route('PUT', (':id', 'move'), self.moveFileToAssetstore)

    @access.public(scope=TokenScope.DATA_READ)
    @filtermodel(model='file')
    @autoDescribeRoute(
        Description('Get a file\'s information.')
        .modelParam('id', model='file', level=AccessType.READ)
        .errorResponse()
        .errorResponse('Read access was denied on the file.', 403)
    )
    def getFile(self, file, params):
        return file

    @access.user(scope=TokenScope.DATA_WRITE)
    @autoDescribeRoute(
        Description('Start a new upload or create an empty or link file.')
        .responseClass('Upload')
        .param('parentType', 'Type being uploaded into.', enum=['folder', 'item'])
        .param('parentId', 'The ID of the parent.')
        .param('name', 'Name of the file being created.')
        .param('size', 'Size in bytes of the file.', dataType='integer', required=False)
        .param('mimeType', 'The MIME type of the file.', required=False)
        .param('linkUrl', 'If this is a link file, pass its URL instead '
               'of size and mimeType using this parameter.', required=False)
        .param('reference', 'If included, this information is passed to the '
               'data.process event when the upload is complete.',
               required=False)
        .param('assetstoreId', 'Direct the upload to a specific assetstore (admin-only).',
               required=False)
        .errorResponse()
        .errorResponse('Write access was denied on the parent folder.', 403)
        .errorResponse('Failed to create upload.', 500)
    )
    def initUpload(self, parentType, parentId, name, size, mimeType, linkUrl, reference,
                   assetstoreId, params):
        """
        Before any bytes of the actual file are sent, a request should be made
        to initialize the upload. This creates the temporary record of the
        forthcoming upload that will be passed in chunks to the readChunk
        method. If you pass a "linkUrl" parameter, it will make a link file
        in the designated parent.
        """
        user = self.getCurrentUser()
        parent = self.model(parentType).load(
            id=parentId, user=user, level=AccessType.WRITE, exc=True)

        if linkUrl is not None:
            return self.model('file').filter(
                self.model('file').createLinkFile(
                    url=linkUrl, parent=parent, name=name, parentType=parentType, creator=user,
                    size=size, mimeType=mimeType), user)
        else:
            self.requireParams({'size': size})
            assetstore = None
            if assetstoreId:
                self.requireAdmin(
                    user, message='You must be an admin to select a destination assetstore.')
                assetstore = self.model('assetstore').load(assetstoreId)
            try:
                upload = self.model('upload').createUpload(
                    user=user, name=name, parentType=parentType, parent=parent, size=size,
                    mimeType=mimeType, reference=reference, assetstore=assetstore)
            except OSError as exc:
                if exc.errno == errno.EACCES:
                    raise GirderException(
                        'Failed to create upload.', 'girder.api.v1.file.create-upload-failed')
                raise
            if upload['size'] > 0:
                return upload
            else:
                return self.model('file').filter(
                    self.model('upload').finalizeUpload(upload), user)

    @access.user(scope=TokenScope.DATA_WRITE)
    @autoDescribeRoute(
        Description('Finalize an upload explicitly if necessary.')
        .notes('This is only required in certain non-standard upload '
               'behaviors. Clients should know which behavior models require '
               'the finalize step to be called in their behavior handlers.')
        .modelParam('uploadId', paramType='formData')
        .errorResponse(('ID was invalid.',
                        'The upload does not require finalization.',
                        'Not enough bytes have been uploaded.'))
        .errorResponse('You are not the user who initiated the upload.', 403)
    )
    def finalizeUpload(self, upload, params):
        user = self.getCurrentUser()

        if upload['userId'] != user['_id']:
            raise AccessException('You did not initiate this upload.')

        # If we don't have as much data as we were told would be uploaded and
        # the upload hasn't specified it has an alternate behavior, refuse to
        # complete the upload.
        if upload['received'] != upload['size'] and 'behavior' not in upload:
            raise RestException(
                'Server has only received %s bytes, but the file should be %s bytes.' %
                (upload['received'], upload['size']))

        file = self.model('upload').finalizeUpload(upload)
        extraKeys = file.get('additionalFinalizeKeys', ())
        return self.model('file').filter(file, user, additionalKeys=extraKeys)

    @access.user(scope=TokenScope.DATA_WRITE)
    @autoDescribeRoute(
        Description('Request required offset before resuming an upload.')
        .modelParam('uploadId', paramType='formData')
        .errorResponse("The ID was invalid, or the offset did not match the server's record.")
    )
    def requestOffset(self, upload, params):
        """
        This should be called when resuming an interrupted upload. It will
        report the offset into the upload that should be used to resume.
        :param uploadId: The _id of the temp upload record being resumed.
        :returns: The offset in bytes that the client should use.
        """
        offset = self.model('upload').requestOffset(upload)

        if isinstance(offset, six.integer_types):
            upload['received'] = offset
            self.model('upload').save(upload)
            return {'offset': offset}
        else:
            return offset

    @access.user(scope=TokenScope.DATA_WRITE)
    @autoDescribeRoute(
        Description('Upload a chunk of a file.')
        .modelParam('uploadId', paramType='formData')
        .param('offset', 'Offset of the chunk in the file.', dataType='integer',
               paramType='formData')
        .errorResponse(('ID was invalid.',
                        'Received too many bytes.',
                        'Chunk is smaller than the minimum size.'))
        .errorResponse('You are not the user who initiated the upload.', 403)
        .errorResponse('Failed to store upload.', 500)
    )
    def readChunk(self, upload, offset, params):
        """
        After the temporary upload record has been created (see initUpload),
        the bytes themselves should be passed up in ordered chunks. The user
        must remain logged in when passing each chunk, to authenticate that
        the writer of the chunk is the same as the person who initiated the
        upload. The passed offset is a verification mechanism for ensuring the
        server and client agree on the number of bytes sent/received.

        This method accepts both the legacy multipart content encoding, as
        well as passing offset and uploadId as query parameters and passing
        the chunk as the body, which is the recommended method.

        Multipart uploads are @deprecated as of v2.2.0.
        """
        if 'chunk' in params:
            chunk = params['chunk']
            if isinstance(chunk, cherrypy._cpreqbody.Part):
                # Seek is the only obvious way to get the length of the part
                chunk.file.seek(0, os.SEEK_END)
                size = chunk.file.tell()
                chunk.file.seek(0, os.SEEK_SET)
                chunk = RequestBodyStream(chunk.file, size=size)
        else:
            chunk = RequestBodyStream(cherrypy.request.body)

        user = self.getCurrentUser()

        if upload['userId'] != user['_id']:
            raise AccessException('You did not initiate this upload.')

        if upload['received'] != offset:
            raise RestException(
                'Server has received %s bytes, but client sent offset %s.' % (
                    upload['received'], offset))
        try:
            return self.model('upload').handleChunk(upload, chunk, filter=True, user=user)
        except IOError as exc:
            if exc.errno == errno.EACCES:
                raise Exception('Failed to store upload.')
            raise

    @access.cookie
    @access.public(scope=TokenScope.DATA_READ)
    @autoDescribeRoute(
        Description('Download a file.')
        .notes('This endpoint also accepts the HTTP "Range" header for partial '
               'file downloads.')
        .modelParam('id', model='file', level=AccessType.READ)
        .param('offset', 'Start downloading at this offset in bytes within '
               'the file.', dataType='integer', required=False, default=0)
        .param('endByte', 'If you only wish to download part of the file, '
               'pass this as the index of the last byte to download. Unlike '
               'the HTTP Range header, the endByte parameter is non-inclusive, '
               'so you should set it to the index of the byte one past the '
               'final byte you wish to receive.', dataType='integer',
               required=False)
        .param('contentDisposition', 'Specify the Content-Disposition response '
               'header disposition-type value.', required=False,
               enum=['inline', 'attachment'], default='attachment')
        .param('extraParameters', 'Arbitrary data to send along with the download request.',
               required=False)
        .errorResponse('ID was invalid.')
        .errorResponse('Read access was denied on the parent folder.', 403)
    )
    def download(self, file, offset, endByte, contentDisposition, extraParameters, params):
        """
        Defers to the underlying assetstore adapter to stream a file out.
        Requires read permission on the folder that contains the file's item.
        """
        rangeHeader = cherrypy.lib.httputil.get_ranges(
            cherrypy.request.headers.get('Range'), file.get('size', 0))

        # The HTTP Range header takes precedence over query params
        if rangeHeader and len(rangeHeader):
            # Currently we only support a single range.
            offset, endByte = rangeHeader[0]

        return self.model('file').download(
            file, offset, endByte=endByte, contentDisposition=contentDisposition,
            extraParameters=extraParameters)

    @access.cookie
    @access.public(scope=TokenScope.DATA_READ)
    @describeRoute(
        Description('Download a file.')
        .param('id', 'The ID of the file.', paramType='path')
        .param('name', 'The name of the file.  This is ignored.',
               paramType='path')
        .param('offset', 'Start downloading at this offset in bytes within '
               'the file.', dataType='integer', required=False)
        .notes('The name parameter doesn\'t alter the download.  Some '
               'download clients save files based on the last part of a path, '
               'and specifying the name satisfies those clients.')
        .errorResponse('ID was invalid.')
        .errorResponse('Read access was denied on the parent folder.', 403)
    )
    def downloadWithName(self, id, name, params):
        return self.download(id=id, params=params)

    @access.user(scope=TokenScope.DATA_WRITE)
    @autoDescribeRoute(
        Description('Delete a file by ID.')
        .modelParam('id', model='file', level=AccessType.WRITE)
        .errorResponse('ID was invalid.')
        .errorResponse('Write access was denied on the parent folder.', 403)
    )
    def deleteFile(self, file, params):
        self.model('file').remove(file)

    @access.user(scope=TokenScope.DATA_WRITE)
    @autoDescribeRoute(
        Description('Cancel a partially completed upload.')
        .modelParam('id', model='upload')
        .errorResponse('ID was invalid.')
        .errorResponse('You lack permission to cancel this upload.', 403)
    )
    def cancelUpload(self, upload, params):
        user = self.getCurrentUser()

        if upload['userId'] != user['_id'] and not user['admin']:
            raise AccessException('You did not initiate this upload.')

        self.model('upload').cancelUpload(upload)
        return {'message': 'Upload canceled.'}

    @access.user(scope=TokenScope.DATA_WRITE)
    @filtermodel(model='file')
    @autoDescribeRoute(
        Description('Change file metadata such as name or MIME type.')
        .modelParam('id', model='file', level=AccessType.WRITE)
        .param('name', 'The name to set on the file.', required=False, strip=True)
        .param('mimeType', 'The MIME type of the file.', required=False, strip=True)
        .errorResponse('ID was invalid.')
        .errorResponse('Write access was denied on the parent folder.', 403)
    )
    def updateFile(self, file, name, mimeType, params):
        if name is not None:
            file['name'] = name
        if mimeType is not None:
            file['mimeType'] = mimeType

        return self.model('file').updateFile(file)

    @access.user(scope=TokenScope.DATA_WRITE)
    @autoDescribeRoute(
        Description('Change the contents of an existing file.')
        .modelParam('id', model='file', level=AccessType.WRITE)
        .param('size', 'Size in bytes of the new file.', dataType='integer')
        .param('reference', 'If included, this information is passed to the '
               'data.process event when the upload is complete.',
               required=False)
        .param('assetstoreId', 'Direct the upload to a specific assetstore (admin-only).',
               required=False)
        .notes('After calling this, send the chunks just like you would with a '
               'normal file upload.')
    )
    def updateFileContents(self, file, size, reference, assetstoreId, params):
        user = self.getCurrentUser()

        assetstore = None
        if assetstoreId:
            self.requireAdmin(
                user, message='You must be an admin to select a destination assetstore.')
            assetstore = self.model('assetstore').load(assetstoreId)
        # Create a new upload record into the existing file
        upload = self.model('upload').createUploadToFile(
            file=file, user=user, size=size, reference=reference, assetstore=assetstore)

        if upload['size'] > 0:
            return upload
        else:
            return self.model('file').filter(self.model('upload').finalizeUpload(upload), user)

    @access.admin(scope=TokenScope.DATA_WRITE)
    @filtermodel(model='file')
    @autoDescribeRoute(
        Description('Move a file to a different assetstore.')
        .modelParam('id', model='file', level=AccessType.WRITE)
        .modelParam('assetstoreId', 'The destination assetstore.', paramType='formData')
        .param('progress', 'Controls whether progress notifications will be sent.',
               dataType='boolean', default=False, required=False)
    )
    def moveFileToAssetstore(self, file, assetstore, progress, params):
        user = self.getCurrentUser()
        title = 'Moving file "%s" to assetstore "%s"' % (file['name'], assetstore['name'])

        with ProgressContext(progress, user=user, title=title, total=file['size']) as ctx:
            return self.model('upload').moveFileToAssetstore(
                file=file, user=user, assetstore=assetstore, progress=ctx)

    @access.user(scope=TokenScope.DATA_WRITE)
    @filtermodel(model='file')
    @autoDescribeRoute(
        Description('Copy a file.')
        .modelParam('id', model='file', level=AccessType.READ)
        .modelParam('itemId', description='The ID of the item to copy the file to.',
                    level=AccessType.WRITE, paramType='formData')
    )
    def copy(self, file, item, params):
        return self.model('file').copyFile(file, self.getCurrentUser(), item=item)
