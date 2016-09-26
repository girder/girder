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
import six

from ..describe import Description, describeRoute
from ..rest import Resource, RestException, filtermodel, loadmodel
from ...constants import AccessType, TokenScope
from girder.models.model_base import AccessException, GirderException
from girder.api import access


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
    @loadmodel(model='file', level=AccessType.READ)
    @filtermodel(model='file')
    @describeRoute(
        Description('Get a file\'s information.')
        .param('id', 'The ID of the file.', paramType='path')
        .errorResponse()
        .errorResponse('Read access was denied on the file.', 403)
    )
    def getFile(self, file, params):
        return file

    @access.user(scope=TokenScope.DATA_WRITE)
    @describeRoute(
        Description('Start a new upload or create an empty or link file.')
        .responseClass('Upload')
        .param('parentType', 'Type being uploaded into (folder or item).')
        .param('parentId', 'The ID of the parent.')
        .param('name', 'Name of the file being created.')
        .param('size', 'Size in bytes of the file.',
               dataType='integer', required=False)
        .param('mimeType', 'The MIME type of the file.', required=False)
        .param('linkUrl', 'If this is a link file, pass its URL instead '
               'of size and mimeType using this parameter.', required=False)
        .param('reference', 'If included, this information is passed to the '
               'data.process event when the upload is complete.',
               required=False)
        .param('assetstoreId', 'Direct the upload to a specific assetstore.',
               required=False)
        .errorResponse()
        .errorResponse('Write access was denied on the parent folder.', 403)
        .errorResponse('Failed to create upload.', 500)
    )
    def initUpload(self, params):
        """
        Before any bytes of the actual file are sent, a request should be made
        to initialize the upload. This creates the temporary record of the
        forthcoming upload that will be passed in chunks to the readChunk
        method. If you pass a "linkUrl" parameter, it will make a link file
        in the designated parent.
        """
        self.requireParams(('name', 'parentId', 'parentType'), params)
        user = self.getCurrentUser()

        mimeType = params.get('mimeType', 'application/octet-stream')
        parentType = params['parentType'].lower()

        if parentType not in ('folder', 'item'):
            raise RestException('The parentType must be "folder" or "item".')

        parent = self.model(parentType).load(id=params['parentId'], user=user,
                                             level=AccessType.WRITE, exc=True)

        if 'linkUrl' in params:
            return self.model('file').filter(
                self.model('file').createLinkFile(
                    url=params['linkUrl'], parent=parent, name=params['name'],
                    parentType=parentType, creator=user), user)
        else:
            self.requireParams('size', params)
            assetstore = None
            if params.get('assetstoreId'):
                assetstore = self.model('assetstore').load(
                    params['assetstoreId'])
            try:
                upload = self.model('upload').createUpload(
                    user=user, name=params['name'], parentType=parentType,
                    parent=parent, size=int(params['size']), mimeType=mimeType,
                    reference=params.get('reference'), assetstore=assetstore)
            except OSError as exc:
                if exc.errno == errno.EACCES:
                    raise GirderException(
                        'Failed to create upload.',
                        'girder.api.v1.file.create-upload-failed')
                raise
            if upload['size'] > 0:
                return upload
            else:
                return self.model('file').filter(
                    self.model('upload').finalizeUpload(upload), user)

    @access.user(scope=TokenScope.DATA_WRITE)
    @describeRoute(
        Description('Finalize an upload explicitly if necessary.')
        .notes('This is only required in certain non-standard upload '
               'behaviors. Clients should know which behavior models require '
               'the finalize step to be called in their behavior handlers.')
        .param('uploadId', 'The ID of the upload record.', paramType='formData')
        .errorResponse(('ID was invalid.',
                        'The upload does not require finalization.',
                        'Not enough bytes have been uploaded.'))
        .errorResponse('You are not the user who initiated the upload.', 403)
    )
    def finalizeUpload(self, params):
        self.requireParams('uploadId', params)
        user = self.getCurrentUser()

        upload = self.model('upload').load(params['uploadId'], exc=True)

        if upload['userId'] != user['_id']:
            raise AccessException('You did not initiate this upload.')

        # If we don't have as much data as we were told would be uploaded and
        # the upload hasn't specified it has an alternate behavior, refuse to
        # complete the upload.
        if upload['received'] != upload['size'] and 'behavior' not in upload:
            raise RestException(
                'Server has only received %s bytes, but the file should be %s '
                'bytes.' % (upload['received'], upload['size']))

        file = self.model('upload').finalizeUpload(upload)
        extraKeys = file.get('additionalFinalizeKeys', ())
        return self.model('file').filter(file, user, additionalKeys=extraKeys)

    @access.user(scope=TokenScope.DATA_WRITE)
    @describeRoute(
        Description('Request required offset before resuming an upload.')
        .param('uploadId', 'The ID of the upload record.')
        .errorResponse("The ID was invalid, or the offset did not match the "
                       "server's record.")
    )
    def requestOffset(self, params):
        """
        This should be called when resuming an interrupted upload. It will
        report the offset into the upload that should be used to resume.
        :param uploadId: The _id of the temp upload record being resumed.
        :returns: The offset in bytes that the client should use.
        """
        self.requireParams('uploadId', params)
        upload = self.model('upload').load(params['uploadId'], exc=True)
        offset = self.model('upload').requestOffset(upload)

        if isinstance(offset, six.integer_types):
            upload['received'] = offset
            self.model('upload').save(upload)
            return {'offset': offset}
        else:
            return offset

    @access.user(scope=TokenScope.DATA_WRITE)
    @describeRoute(
        Description('Upload a chunk of a file with multipart/form-data.')
        .consumes('multipart/form-data')
        .param('uploadId', 'The ID of the upload record.', paramType='formData')
        .param('offset', 'Offset of the chunk in the file.', dataType='integer',
               paramType='formData')
        .param('chunk', 'The actual bytes of the chunk. For external upload '
               'behaviors, this may be set to an opaque string that will be '
               'handled by the assetstore adapter.',
               dataType='file', paramType='formData')
        .errorResponse(('ID was invalid.',
                        'Received too many bytes.',
                        'Chunk is smaller than the minimum size.'))
        .errorResponse('You are not the user who initiated the upload.', 403)
        .errorResponse('Failed to store upload.', 500)
    )
    def readChunk(self, params):
        """
        After the temporary upload record has been created (see initUpload),
        the bytes themselves should be passed up in ordered chunks. The user
        must remain logged in when passing each chunk, to authenticate that
        the writer of the chunk is the same as the person who initiated the
        upload. The passed offset is a verification mechanism for ensuring the
        server and client agree on the number of bytes sent/received.
        """
        self.requireParams(('offset', 'uploadId', 'chunk'), params)

        user = self.getCurrentUser()
        upload = self.model('upload').load(params['uploadId'], exc=True)
        offset = int(params['offset'])
        chunk = params['chunk']

        if upload['userId'] != user['_id']:
            raise AccessException('You did not initiate this upload.')

        if upload['received'] != offset:
            raise RestException(
                'Server has received %s bytes, but client sent offset %s.' % (
                    upload['received'], offset))
        try:
            if isinstance(chunk, cherrypy._cpreqbody.Part):
                return self.model('upload').handleChunk(upload, chunk.file)
            else:
                return self.model('upload').handleChunk(upload, chunk)
        except IOError as exc:
            if exc.errno == errno.EACCES:
                raise Exception('Failed to store upload.')
            raise

    @access.cookie
    @access.public(scope=TokenScope.DATA_READ)
    @loadmodel(model='file', level=AccessType.READ)
    @describeRoute(
        Description('Download a file.')
        .notes('This endpoint also accepts the HTTP "Range" header for partial '
               'file downloads.')
        .param('id', 'The ID of the file.', paramType='path')
        .param('offset', 'Start downloading at this offset in bytes within '
               'the file.', dataType='integer', required=False)
        .param('endByte', 'If you only wish to download part of the file, '
               'pass this as the index of the last byte to download. Unlike '
               'the HTTP Range header, the endByte parameter is non-inclusive, '
               'so you should set it to the index of the byte one past the '
               'final byte you wish to receive.', dataType='integer',
               required=False)
        .param('contentDisposition', 'Specify the Content-Disposition response '
               'header disposition-type value', required=False,
               enum=['inline', 'attachment'], default='attachment')
        .param('extraParameters', 'Arbitrary data to send along with the '
               'download request.', required=False)
        .errorResponse('ID was invalid.')
        .errorResponse('Read access was denied on the parent folder.', 403)
    )
    def download(self, file, params):
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
        else:
            offset = int(params.get('offset', 0))
            endByte = params.get('endByte')

            if endByte is not None:
                endByte = int(endByte)

        contentDisp = params.get('contentDisposition', None)
        if (contentDisp is not None and
           contentDisp not in {'inline', 'attachment'}):
            raise RestException('Unallowed contentDisposition type "%s".' %
                                contentDisp)

        extraParameters = params.get('extraParameters')

        return self.model('file').download(file, offset, endByte=endByte,
                                           contentDisposition=contentDisp,
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
    @loadmodel(model='file', level=AccessType.WRITE)
    @describeRoute(
        Description('Delete a file by ID.')
        .param('id', 'The ID of the file.', paramType='path')
        .errorResponse('ID was invalid.')
        .errorResponse('Write access was denied on the parent folder.', 403)
    )
    def deleteFile(self, file, params):
        self.model('file').remove(file)

    @access.user(scope=TokenScope.DATA_WRITE)
    @loadmodel(model='upload')
    @describeRoute(
        Description('Cancel a partially completed upload.')
        .param('id', 'The ID of the upload.', paramType='path')
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
    @loadmodel(model='file', level=AccessType.WRITE)
    @filtermodel(model='file')
    @describeRoute(
        Description('Change file metadata such as name or MIME type.')
        .param('id', 'The ID of the file.', paramType='path')
        .param('name', 'The name to set on the file.', required=False)
        .param('mimeType', 'The MIME type of the file.', required=False)
        .errorResponse('ID was invalid.')
        .errorResponse('Write access was denied on the parent folder.', 403)
    )
    def updateFile(self, file, params):
        file['name'] = params.get('name', file['name']).strip()
        file['mimeType'] = params.get('mimeType',
                                      (file.get('mimeType') or '').strip())
        return self.model('file').updateFile(file)

    @access.user(scope=TokenScope.DATA_WRITE)
    @loadmodel(model='file', level=AccessType.WRITE)
    @describeRoute(
        Description('Change the contents of an existing file.')
        .param('id', 'The ID of the file.', paramType='path')
        .param('size', 'Size in bytes of the new file.', dataType='integer')
        .param('reference', 'If included, this information is passed to the '
               'data.process event when the upload is complete.',
               required=False)
        .param('assetstoreId', 'Direct the upload to a specific assetstore.',
               required=False)
        .notes('After calling this, send the chunks just like you would with a '
               'normal file upload.')
    )
    def updateFileContents(self, file, params):
        self.requireParams('size', params)
        user = self.getCurrentUser()

        assetstore = None
        if params.get('assetstoreId'):
            assetstore = self.model('assetstore').load(params['assetstoreId'])
        # Create a new upload record into the existing file
        upload = self.model('upload').createUploadToFile(
            file=file, user=user, size=int(params['size']),
            reference=params.get('reference'), assetstore=assetstore)

        if upload['size'] > 0:
            return upload
        else:
            return self.model('file').filter(
                self.model('upload').finalizeUpload(upload), user)

    @access.user(scope=TokenScope.DATA_WRITE)
    @loadmodel(model='file', level=AccessType.WRITE)
    @describeRoute(
        Description('Move a file to a different assetstore.')
        .param('id', 'The ID of the file.', paramType='path')
        .param('assetstoreId', 'The destination assetstore.')
    )
    def moveFileToAssetstore(self, file, params):
        self.requireParams('assetstoreId', params)
        user = self.getCurrentUser()
        assetstore = self.model('assetstore').load(params['assetstoreId'])
        return self.model('upload').moveFileToAssetstore(
            file=file, user=user, assetstore=assetstore)

    @access.user(scope=TokenScope.DATA_WRITE)
    @loadmodel(model='file', level=AccessType.READ)
    @loadmodel(model='item', map={'itemId': 'item'}, level=AccessType.WRITE)
    @filtermodel(model='file')
    @describeRoute(
        Description('Copy a file.')
        .param('id', 'The ID of the file.', paramType='path')
        .param('itemId', 'The item to copy the file to.', required=True)
    )
    def copy(self, file, item, params):
        return self.model('file').copyFile(
            file, self.getCurrentUser(), item=item)
