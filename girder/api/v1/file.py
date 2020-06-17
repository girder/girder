# -*- coding: utf-8 -*-
import cherrypy
import errno

from ..describe import Description, autoDescribeRoute, describeRoute
from ..rest import Resource, filtermodel
from ...constants import AccessType, TokenScope
from girder.exceptions import AccessException, GirderException, RestException
from girder.models.assetstore import Assetstore
from girder.models.file import File as FileModel
from girder.models.item import Item
from girder.models.upload import Upload
from girder.api import access
from girder.utility import RequestBodyStream
from girder.utility.model_importer import ModelImporter
from girder.utility.progress import ProgressContext


class File(Resource):
    """
    API Endpoint for files. Includes utilities for uploading and downloading
    them.
    """

    def __init__(self):
        super().__init__()
        self._model = FileModel()

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
    @filtermodel(model=FileModel)
    @autoDescribeRoute(
        Description("Get a file's information.")
        .modelParam('id', model=FileModel, level=AccessType.READ)
        .errorResponse()
        .errorResponse('Read access was denied on the file.', 403)
    )
    def getFile(self, file):
        return file

    @access.user(scope=TokenScope.DATA_WRITE)
    @autoDescribeRoute(
        Description('Start a new upload or create an empty or link file.')
        .notes('Use POST /file/chunk to send the contents of the file.  '
               'The data for the first chunk of the file can be included with '
               'this query by sending it as the body of the request using an '
               'appropriate content-type and with the other parameters as '
               'part of the query string.  If the entire file is uploaded via '
               'this call, the resulting file is returned.')
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
                   assetstoreId):
        """
        Before any bytes of the actual file are sent, a request should be made
        to initialize the upload. This creates the temporary record of the
        forthcoming upload that will be passed in chunks to the readChunk
        method. If you pass a "linkUrl" parameter, it will make a link file
        in the designated parent.
        """
        user = self.getCurrentUser()
        parent = ModelImporter.model(parentType).load(
            id=parentId, user=user, level=AccessType.WRITE, exc=True)

        if linkUrl is not None:
            return self._model.filter(
                self._model.createLinkFile(
                    url=linkUrl, parent=parent, name=name, parentType=parentType, creator=user,
                    size=size, mimeType=mimeType), user)
        else:
            self.requireParams({'size': size})
            assetstore = None
            if assetstoreId:
                self.requireAdmin(
                    user, message='You must be an admin to select a destination assetstore.')
                assetstore = Assetstore().load(assetstoreId)

            chunk = None
            if size > 0 and cherrypy.request.headers.get('Content-Length'):
                ct = cherrypy.request.body.content_type.value
                if (ct not in cherrypy.request.body.processors
                        and ct.split('/', 1)[0] not in cherrypy.request.body.processors):
                    chunk = RequestBodyStream(cherrypy.request.body)
            if chunk is not None and chunk.getSize() <= 0:
                chunk = None

            try:
                # TODO: This can be made more efficient by adding
                #    save=chunk is None
                # to the createUpload call parameters.  However, since this is
                # a breaking change, that should be deferred until a major
                # version upgrade.
                upload = Upload().createUpload(
                    user=user, name=name, parentType=parentType, parent=parent, size=size,
                    mimeType=mimeType, reference=reference, assetstore=assetstore)
            except OSError as exc:
                if exc.errno == errno.EACCES:
                    raise GirderException(
                        'Failed to create upload.', 'girder.api.v1.file.create-upload-failed')
                raise
            if upload['size'] > 0:
                if chunk:
                    return Upload().handleChunk(upload, chunk, filter=True, user=user)

                return upload
            else:
                return self._model.filter(Upload().finalizeUpload(upload), user)

    @access.user(scope=TokenScope.DATA_WRITE)
    @autoDescribeRoute(
        Description('Finalize an upload explicitly if necessary.')
        .notes('This is only required in certain non-standard upload '
               'behaviors. Clients should know which behavior models require '
               'the finalize step to be called in their behavior handlers.')
        .modelParam('uploadId', paramType='formData', model=Upload)
        .errorResponse(('ID was invalid.',
                        'The upload does not require finalization.',
                        'Not enough bytes have been uploaded.'))
        .errorResponse('You are not the user who initiated the upload.', 403)
    )
    def finalizeUpload(self, upload):
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

        file = Upload().finalizeUpload(upload)
        extraKeys = file.get('additionalFinalizeKeys', ())
        return self._model.filter(file, user, additionalKeys=extraKeys)

    @access.user(scope=TokenScope.DATA_WRITE)
    @autoDescribeRoute(
        Description('Request required offset before resuming an upload.')
        .modelParam('uploadId', paramType='formData', model=Upload)
        .errorResponse("The ID was invalid, or the offset did not match the server's record.")
    )
    def requestOffset(self, upload):
        """
        This should be called when resuming an interrupted upload. It will
        report the offset into the upload that should be used to resume.
        :param uploadId: The _id of the temp upload record being resumed.
        :returns: The offset in bytes that the client should use.
        """
        offset = Upload().requestOffset(upload)

        if isinstance(offset, int):
            upload['received'] = offset
            Upload().save(upload)
            return {'offset': offset}
        else:
            return offset

    @access.user(scope=TokenScope.DATA_WRITE)
    @autoDescribeRoute(
        Description('Upload a chunk of a file.')
        .notes('The data for the chunk should be sent as the body of the '
               'request using an appropriate content-type and with the other '
               'parameters as part of the query string.')
        .modelParam('uploadId', paramType='formData', model=Upload)
        .param('offset', 'Offset of the chunk in the file.', dataType='integer',
               paramType='query', required=False, default=0)
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
        """
        if cherrypy.request.headers.get('Content-Type', '').startswith('multipart/form-data'):
            raise RestException('Multipart encoding is no longer supported. Send the chunk in '
                                'the request body, and other parameters in the query string.')

        if 'chunk' in params:
            # If we see the undocumented "chunk" query string parameter, then we abort trying to
            # read the body, use the query string value as chunk, and pass it through to
            # Upload().handleChunk. This case is used by the direct S3 upload process.
            chunk = params['chunk']
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
            return Upload().handleChunk(upload, chunk, filter=True, user=user)
        except IOError as exc:
            if exc.errno == errno.EACCES:
                raise Exception('Failed to store upload.')
            raise

    @access.public(scope=TokenScope.DATA_READ, cookie=True)
    @autoDescribeRoute(
        Description('Download a file.')
        .notes('This endpoint also accepts the HTTP "Range" header for partial '
               'file downloads.')
        .modelParam('id', model=FileModel, level=AccessType.READ)
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
    def download(self, file, offset, endByte, contentDisposition, extraParameters):
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

        return self._model.download(
            file, offset, endByte=endByte, contentDisposition=contentDisposition,
            extraParameters=extraParameters)

    @access.public(scope=TokenScope.DATA_READ, cookie=True)
    @describeRoute(
        Description('Download a file.')
        .param('id', 'The ID of the file.', paramType='path')
        .param('name', 'The name of the file.  This is ignored.',
               paramType='path')
        .param('offset', 'Start downloading at this offset in bytes within '
               'the file.', dataType='integer', required=False)
        .notes("The name parameter doesn't alter the download.  Some "
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
        .modelParam('id', model=FileModel, level=AccessType.WRITE)
        .errorResponse('ID was invalid.')
        .errorResponse('Write access was denied on the parent folder.', 403)
    )
    def deleteFile(self, file):
        self._model.remove(file)

    @access.user(scope=TokenScope.DATA_WRITE)
    @autoDescribeRoute(
        Description('Cancel a partially completed upload.')
        .modelParam('id', model=Upload)
        .errorResponse('ID was invalid.')
        .errorResponse('You lack permission to cancel this upload.', 403)
    )
    def cancelUpload(self, upload):
        user = self.getCurrentUser()

        if upload['userId'] != user['_id'] and not user['admin']:
            raise AccessException('You did not initiate this upload.')

        Upload().cancelUpload(upload)
        return {'message': 'Upload canceled.'}

    @access.user(scope=TokenScope.DATA_WRITE)
    @filtermodel(model=FileModel)
    @autoDescribeRoute(
        Description('Change file metadata such as name or MIME type.')
        .modelParam('id', model=FileModel, level=AccessType.WRITE)
        .param('name', 'The name to set on the file.', required=False, strip=True)
        .param('mimeType', 'The MIME type of the file.', required=False, strip=True)
        .errorResponse('ID was invalid.')
        .errorResponse('Write access was denied on the parent folder.', 403)
    )
    def updateFile(self, file, name, mimeType):
        if name is not None:
            file['name'] = name
        if mimeType is not None:
            file['mimeType'] = mimeType

        return self._model.updateFile(file)

    @access.user(scope=TokenScope.DATA_WRITE)
    @autoDescribeRoute(
        Description('Change the contents of an existing file.')
        .modelParam('id', model=FileModel, level=AccessType.WRITE)
        .param('size', 'Size in bytes of the new file.', dataType='integer')
        .param('reference', 'If included, this information is passed to the '
               'data.process event when the upload is complete.', required=False)
        .param('assetstoreId', 'Direct the upload to a specific assetstore (admin-only).',
               required=False)
        .notes('After calling this, send the chunks just like you would with a '
               'normal file upload.')
    )
    def updateFileContents(self, file, size, reference, assetstoreId):
        user = self.getCurrentUser()

        assetstore = None
        if assetstoreId:
            self.requireAdmin(
                user, message='You must be an admin to select a destination assetstore.')
            assetstore = Assetstore().load(assetstoreId)
        # Create a new upload record into the existing file
        upload = Upload().createUploadToFile(
            file=file, user=user, size=size, reference=reference, assetstore=assetstore)

        if upload['size'] > 0:
            return upload
        else:
            return self._model.filter(Upload().finalizeUpload(upload), user)

    @access.admin(scope=TokenScope.DATA_WRITE)
    @filtermodel(model=FileModel)
    @autoDescribeRoute(
        Description('Move a file to a different assetstore.')
        .modelParam('id', model=FileModel, level=AccessType.WRITE)
        .modelParam('assetstoreId', 'The destination assetstore.', paramType='formData',
                    model=Assetstore)
        .param('progress', 'Controls whether progress notifications will be sent.',
               dataType='boolean', default=False, required=False)
    )
    def moveFileToAssetstore(self, file, assetstore, progress):
        user = self.getCurrentUser()
        title = 'Moving file "%s" to assetstore "%s"' % (file['name'], assetstore['name'])

        with ProgressContext(progress, user=user, title=title, total=file['size']) as ctx:
            return Upload().moveFileToAssetstore(
                file=file, user=user, assetstore=assetstore, progress=ctx)

    @access.user(scope=TokenScope.DATA_WRITE)
    @filtermodel(model=FileModel)
    @autoDescribeRoute(
        Description('Copy a file.')
        .modelParam('id', model=FileModel, level=AccessType.READ)
        .modelParam('itemId', description='The ID of the item to copy the file to.',
                    level=AccessType.WRITE, paramType='formData', model=Item)
    )
    def copy(self, file, item):
        return self._model.copyFile(file, self.getCurrentUser(), item=item)
