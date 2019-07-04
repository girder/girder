# -*- coding: utf-8 -*-
from ..describe import Description, autoDescribeRoute
from ..rest import Resource, filtermodel, setResponseHeader, setContentDisposition
from girder.utility import ziputil
from girder.constants import AccessType, TokenScope
from girder.exceptions import RestException
from girder.api import access
from girder.models.file import File
from girder.models.folder import Folder
from girder.models.item import Item as ItemModel


class Item(Resource):

    def __init__(self):
        super(Item, self).__init__()
        self.resourceName = 'item'
        self._model = ItemModel()

        self.route('DELETE', (':id',), self.deleteItem)
        self.route('GET', (), self.find)
        self.route('GET', (':id',), self.getItem)
        self.route('GET', (':id', 'files'), self.getFiles)
        self.route('GET', (':id', 'download'), self.download)
        self.route('GET', (':id', 'rootpath'), self.rootpath)
        self.route('POST', (), self.createItem)
        self.route('PUT', (':id',), self.updateItem)
        self.route('POST', (':id', 'copy'), self.copyItem)
        self.route('PUT', (':id', 'metadata'), self.setMetadata)
        self.route('DELETE', (':id', 'metadata'), self.deleteMetadata)

    @access.public(scope=TokenScope.DATA_READ)
    @filtermodel(model=ItemModel)
    @autoDescribeRoute(
        Description('List or search for items.')
        .notes('You must pass either a "itemId" or "text" field '
               'to specify how you are searching for items.  '
               'If you omit one of these parameters the request will fail and respond : '
               '"Invalid search mode."')
        .responseClass('Item', array=True)
        .param('folderId', 'Pass this to list all items in a folder.',
               required=False)
        .param('text', 'Pass this to perform a full text search for items.',
               required=False)
        .param('name', 'Pass to lookup an item by exact name match. Must '
               'pass folderId as well when using this.', required=False)
        .pagingParams(defaultSort='lowerName')
        .errorResponse()
        .errorResponse('Read access was denied on the parent folder.', 403)
    )
    def find(self, folderId, text, name, limit, offset, sort):
        """
        Get a list of items with given search parameters. Currently accepted
        search modes are:

        1. Searching by folderId, with optional additional filtering by the name
           field (exact match) or using full text search within a single parent
           folder. Pass a "name" parameter or "text" parameter to invoke these
           additional filters.
        2. Searching with full text search across all items in the system.
           Simply pass a "text" parameter for this mode.
        """
        user = self.getCurrentUser()

        if folderId:
            folder = Folder().load(
                id=folderId, user=user, level=AccessType.READ, exc=True)
            filters = {}
            if text:
                filters['$text'] = {
                    '$search': text
                }
            if name:
                filters['name'] = name

            return Folder().childItems(
                folder=folder, limit=limit, offset=offset, sort=sort, filters=filters)
        elif text is not None:
            return self._model.textSearch(
                text, user=user, limit=limit, offset=offset, sort=sort)
        else:
            raise RestException('Invalid search mode.')

    @access.public(scope=TokenScope.DATA_READ)
    @filtermodel(model=ItemModel)
    @autoDescribeRoute(
        Description('Get an item by ID.')
        .responseClass('Item')
        .modelParam('id', model=ItemModel, level=AccessType.READ)
        .errorResponse('ID was invalid.')
        .errorResponse('Read access was denied for the item.', 403)
    )
    def getItem(self, item):
        return item

    @access.user(scope=TokenScope.DATA_WRITE)
    @filtermodel(model=ItemModel)
    @autoDescribeRoute(
        Description('Create a new item.')
        .responseClass('Item')
        .modelParam('folderId', 'The ID of the parent folder.', model=Folder,
                    level=AccessType.WRITE, paramType='query')
        .param('name', 'Name for the item.', strip=True)
        .param('description', 'Description for the item.', required=False,
               default='', strip=True)
        .param('reuseExisting', 'Return existing item (by name) if it exists.',
               required=False, dataType='boolean', default=False)
        .jsonParam('metadata', 'A JSON object containing the metadata keys to add',
                   paramType='form', requireObject=True, required=False)
        .errorResponse()
        .errorResponse('Write access was denied on the parent folder.', 403)
    )
    def createItem(self, folder, name, description, reuseExisting, metadata):
        newItem = self._model.createItem(
            folder=folder, name=name, creator=self.getCurrentUser(), description=description,
            reuseExisting=reuseExisting)
        if metadata:
            newItem = self._model.setMetadata(newItem, metadata)
        return newItem

    @access.user(scope=TokenScope.DATA_WRITE)
    @filtermodel(model=ItemModel)
    @autoDescribeRoute(
        Description('Edit an item or move it to another folder.')
        .responseClass('Item')
        .modelParam('id', model=ItemModel, level=AccessType.WRITE)
        .param('name', 'Name for the item.', required=False, strip=True)
        .param('description', 'Description for the item.', required=False)
        .modelParam('folderId', 'Pass this to move the item to a new folder.', model=Folder,
                    required=False, paramType='query', level=AccessType.WRITE)
        .jsonParam('metadata', 'A JSON object containing the metadata keys to add',
                   paramType='form', requireObject=True, required=False)
        .errorResponse('ID was invalid.')
        .errorResponse('Write access was denied for the item or folder.', 403)
    )
    def updateItem(self, item, name, description, folder, metadata):
        if name is not None:
            item['name'] = name
        if description is not None:
            item['description'] = description

        self._model.updateItem(item)

        if folder and folder['_id'] != item['folderId']:
            self._model.move(item, folder)

        if metadata:
            item = self._model.setMetadata(item, metadata)

        return item

    @access.user(scope=TokenScope.DATA_WRITE)
    @filtermodel(model=ItemModel)
    @autoDescribeRoute(
        Description('Set metadata fields on an item.')
        .responseClass('Item')
        .notes('Set metadata fields to null in order to delete them.')
        .modelParam('id', model=ItemModel, level=AccessType.WRITE)
        .jsonParam('metadata', 'A JSON object containing the metadata keys to add',
                   paramType='body', requireObject=True)
        .param('allowNull', 'Whether "null" is allowed as a metadata value.', required=False,
               dataType='boolean', default=False)
        .errorResponse(('ID was invalid.',
                        'Invalid JSON passed in request body.',
                        'Metadata key name was invalid.'))
        .errorResponse('Write access was denied for the item.', 403)
    )
    def setMetadata(self, item, metadata, allowNull):
        return self._model.setMetadata(item, metadata, allowNull=allowNull)

    @access.user(scope=TokenScope.DATA_WRITE)
    @filtermodel(ItemModel)
    @autoDescribeRoute(
        Description('Delete metadata fields on an item.')
        .responseClass('Item')
        .modelParam('id', model=ItemModel, level=AccessType.WRITE)
        .jsonParam(
            'fields', 'A JSON list containing the metadata fields to delete',
            paramType='body', schema={
                'type': 'array',
                'items': {
                    'type': 'string'
                }
            }
        )
        .errorResponse(('ID was invalid.',
                        'Invalid JSON passed in request body.',
                        'Metadata key name was invalid.'))
        .errorResponse('Write access was denied for the item.', 403)
    )
    def deleteMetadata(self, item, fields):
        return self._model.deleteMetadata(item, fields)

    def _downloadMultifileItem(self, item, user):
        setResponseHeader('Content-Type', 'application/zip')
        setContentDisposition(item['name'] + '.zip')

        def stream():
            zip = ziputil.ZipGenerator(item['name'])
            for (path, file) in self._model.fileList(item, subpath=False):
                for data in zip.addFile(file, path):
                    yield data
            yield zip.footer()
        return stream

    @access.public(scope=TokenScope.DATA_READ)
    @filtermodel(model=File)
    @autoDescribeRoute(
        Description('Get the files within an item.')
        .responseClass('File', array=True)
        .modelParam('id', model=ItemModel, level=AccessType.READ)
        .pagingParams(defaultSort='name')
        .errorResponse('ID was invalid.')
        .errorResponse('Read access was denied for the item.', 403)
    )
    def getFiles(self, item, limit, offset, sort):
        return self._model.childFiles(item=item, limit=limit, offset=offset, sort=sort)

    @access.public(scope=TokenScope.DATA_READ, cookie=True)
    @autoDescribeRoute(
        Description('Download the contents of an item.')
        .modelParam('id', model=ItemModel, level=AccessType.READ)
        .param('offset', 'Byte offset into the file.', dataType='int',
               required=False, default=0)
        .param('format', 'If unspecified, items with one file are downloaded '
               'as that file, and other items are downloaded as a zip '
               "archive.  If 'zip', a zip archive is always sent.",
               required=False)
        .param('contentDisposition', 'Specify the Content-Disposition response '
               'header disposition-type value, only applied for single file '
               'items.', required=False, enum=['inline', 'attachment'],
               default='attachment')
        .param('extraParameters', 'Arbitrary data to send along with the '
               'download request, only applied for single file '
               'items.', required=False)
        # single file items could produce other types, too.
        .produces(['application/zip', 'application/octet-stream'])
        .errorResponse('ID was invalid.')
        .errorResponse('Read access was denied for the item.', 403)
    )
    def download(self, item, offset, format, contentDisposition, extraParameters):
        user = self.getCurrentUser()
        files = list(self._model.childFiles(item=item, limit=2))
        if format not in (None, '', 'zip'):
            raise RestException('Unsupported format: %s.' % format)
        if len(files) == 1 and format != 'zip':
            if contentDisposition not in {None, 'inline', 'attachment'}:
                raise RestException('Unallowed contentDisposition type "%s".' % contentDisposition)
            return File().download(
                files[0], offset, contentDisposition=contentDisposition,
                extraParameters=extraParameters)
        else:
            return self._downloadMultifileItem(item, user)

    @access.user(scope=TokenScope.DATA_WRITE)
    @autoDescribeRoute(
        Description('Delete an item by ID.')
        .modelParam('id', model=ItemModel, level=AccessType.WRITE)
        .errorResponse('ID was invalid.')
        .errorResponse('Write access was denied for the item.', 403)
    )
    def deleteItem(self, item):
        self._model.remove(item)
        return {'message': 'Deleted item %s.' % item['name']}

    @access.public(scope=TokenScope.DATA_READ)
    @autoDescribeRoute(
        Description("Get the path to the root of the item's hierarchy.")
        .modelParam('id', model=ItemModel, level=AccessType.READ)
        .errorResponse('ID was invalid.')
        .errorResponse('Read access was denied for the item.', 403)
    )
    def rootpath(self, item):
        return self._model.parentsToRoot(item, self.getCurrentUser())

    @access.user(scope=TokenScope.DATA_WRITE)
    @filtermodel(model=ItemModel)
    @autoDescribeRoute(
        Description('Copy an item.')
        .notes('If no folderId parameter is specified, creates a copy of the item in '
               'its current containing folder.')
        .responseClass('Item')
        .modelParam('id', 'The ID of the original item.', model=ItemModel, level=AccessType.READ)
        .modelParam('folderId', 'The ID of the parent folder.', required=False, model=Folder,
                    level=AccessType.WRITE, paramType='query')
        .param('name', 'Name for the new item.', required=False, strip=True)
        .param('description', 'Description for the new item.', required=False, strip=True)
        .errorResponse(('A parameter was invalid.',
                        'ID was invalid.'))
        .errorResponse('Read access was denied on the original item.\n\n'
                       'Write access was denied on the parent folder.', 403)
    )
    def copyItem(self, item, folder, name, description):
        user = self.getCurrentUser()

        if folder is None:
            folder = Folder().load(
                id=item['folderId'], user=user, level=AccessType.WRITE, exc=True)
        return self._model.copyItem(
            item, creator=user, name=name, folder=folder, description=description)
