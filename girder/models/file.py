# -*- coding: utf-8 -*-
import cherrypy
import datetime
import os
import six

from .model_base import Model, AccessControlledModel
from girder import auditLogger, events
from girder.constants import AccessType, CoreEventHandler
from girder.exceptions import FilePathException, ValidationException
from girder.models.setting import Setting
from girder.settings import SettingKey
from girder.utility import acl_mixin, path as path_util
from girder.utility.model_importer import ModelImporter


class File(acl_mixin.AccessControlMixin, Model):
    """
    This model represents a File, which is stored in an assetstore.
    """

    def initialize(self):
        from girder.utility import assetstore_utilities

        self.name = 'file'
        self.ensureIndices(
            ['itemId', 'assetstoreId', 'exts']
            + assetstore_utilities.fileIndexFields())
        self.ensureTextIndex({'name': 1})
        self.resourceColl = 'item'
        self.resourceParent = 'itemId'

        self.exposeFields(level=AccessType.READ, fields=(
            '_id', 'mimeType', 'itemId', 'exts', 'name', 'created', 'creatorId',
            'size', 'updated', 'linkUrl'))

        self.exposeFields(level=AccessType.SITE_ADMIN, fields=('assetstoreId',))

        events.bind('model.file.save.created',
                    CoreEventHandler.FILE_PROPAGATE_SIZE,
                    self._propagateSizeToItem)

    def remove(self, file, updateItemSize=True, **kwargs):
        """
        Use the appropriate assetstore adapter for whatever assetstore the
        file is stored in, and call deleteFile on it, then delete the file
        record from the database.

        :param file: The file document to remove.
        :param updateItemSize: Whether to update the item size. Only set this
            to False if you plan to delete the item and do not care about
            updating its size.
        """
        from .item import Item

        if file.get('assetstoreId'):
            self.getAssetstoreAdapter(file).deleteFile(file)

        if file['itemId']:
            item = Item().load(file['itemId'], force=True)
            # files that are linkUrls might not have a size field
            if 'size' in file:
                self.propagateSizeChange(item, -file['size'], updateItemSize)

        Model.remove(self, file)

    def download(self, file, offset=0, headers=True, endByte=None,
                 contentDisposition=None, extraParameters=None):
        """
        Use the appropriate assetstore adapter for whatever assetstore the
        file is stored in, and call downloadFile on it. If the file is a link
        file rather than a file in an assetstore, we redirect to it.

        :param file: The file to download.
        :param offset: The start byte within the file.
        :type offset: int
        :param headers: Whether to set headers (i.e. is this an HTTP request
            for a single file, or something else).
        :type headers: bool
        :param endByte: Final byte to download. If ``None``, downloads to the
            end of the file.
        :type endByte: int or None
        :param contentDisposition: Content-Disposition response header
            disposition-type value.
        :type contentDisposition: str or None
        :type extraParameters: str or None
        """
        events.trigger('model.file.download.request', info={
            'file': file,
            'startByte': offset,
            'endByte': endByte})

        auditLogger.info('file.download', extra={
            'details': {
                'fileId': file['_id'],
                'startByte': offset,
                'endByte': endByte,
                'extraParameters': extraParameters
            }
        })

        if file.get('assetstoreId'):
            try:
                fileDownload = self.getAssetstoreAdapter(file).downloadFile(
                    file, offset=offset, headers=headers, endByte=endByte,
                    contentDisposition=contentDisposition,
                    extraParameters=extraParameters)

                def downloadGenerator():
                    for data in fileDownload():
                        yield data
                    if endByte is None or endByte >= file['size']:
                        events.trigger('model.file.download.complete', info={
                            'file': file,
                            'startByte': offset,
                            'endByte': endByte,
                            'redirect': False})
                return downloadGenerator
            except cherrypy.HTTPRedirect:
                events.trigger('model.file.download.complete', info={
                    'file': file,
                    'startByte': offset,
                    'endByte': endByte,
                    'redirect': True})
                raise
        elif file.get('linkUrl'):
            if headers:
                events.trigger('model.file.download.complete', info={
                    'file': file,
                    'startByte': offset,
                    'endByte': endByte,
                    'redirect': True})
                raise cherrypy.HTTPRedirect(file['linkUrl'])
            else:
                endByte = endByte or len(file['linkUrl'])

                def stream():
                    yield file['linkUrl'][offset:endByte]
                    if endByte >= len(file['linkUrl']):
                        events.trigger('model.file.download.complete', info={
                            'file': file,
                            'startByte': offset,
                            'endByte': endByte,
                            'redirect': False})
                return stream
        else:
            raise Exception('File has no known download mechanism.')

    def validate(self, doc):
        if doc.get('assetstoreId') is None:
            if 'linkUrl' not in doc:
                raise ValidationException(
                    'File must have either an assetstore ID or a link URL.',
                    'linkUrl')
            doc['linkUrl'] = doc['linkUrl'].strip()

            if not doc['linkUrl'].startswith(('http:', 'https:')):
                raise ValidationException(
                    'Linked file URL must start with http: or https:.',
                    'linkUrl')
        if doc.get('assetstoreType'):
            # If assetstore model is overridden, make sure it's a valid model
            self._getAssetstoreModel(doc)
        if 'name' not in doc or not doc['name']:
            raise ValidationException('File name must not be empty.', 'name')

        doc['exts'] = [ext.lower() for ext in doc['name'].split('.')[1:]]

        return doc

    def _getAssetstoreModel(self, file):
        from .assetstore import Assetstore

        if file.get('assetstoreType'):
            try:
                if isinstance(file['assetstoreType'], six.string_types):
                    return ModelImporter.model(file['assetstoreType'])
                else:
                    return ModelImporter.model(*file['assetstoreType'])
            except Exception:
                raise ValidationException(
                    'Invalid assetstore type: %s.' % (file['assetstoreType'],))
        else:
            return Assetstore()

    def createLinkFile(self, name, parent, parentType, url, creator, size=None,
                       mimeType=None, reuseExisting=False):
        """
        Create a file that is a link to a URL, rather than something we maintain
        in an assetstore.

        :param name: The local name for the file.
        :type name: str
        :param parent: The parent object for this file.
        :type parent: girder.models.folder or girder.models.item
        :param parentType: The parent type (folder or item)
        :type parentType: str
        :param url: The URL that this file points to
        :param creator: The user creating the file.
        :type creator: dict
        :param size: The size of the file in bytes. (optional)
        :type size: int
        :param mimeType: The mimeType of the file. (optional)
        :type mimeType: str
        :param reuseExisting: If a file with the same name already exists in
            this location, return it rather than creating a new file.
        :type reuseExisting: bool
        """
        from .item import Item

        if parentType == 'folder':
            # Create a new item with the name of the file.
            item = Item().createItem(
                name=name, creator=creator, folder=parent, reuseExisting=reuseExisting)
        elif parentType == 'item':
            item = parent

        existing = None
        if reuseExisting:
            existing = self.findOne({
                'itemId': item['_id'],
                'name': name
            })

        if existing:
            file = existing
        else:
            file = {
                'created': datetime.datetime.utcnow(),
                'itemId': item['_id'],
                'assetstoreId': None,
                'name': name
            }

        file.update({
            'creatorId': creator['_id'],
            'mimeType': mimeType,
            'linkUrl': url
        })
        if size is not None:
            file['size'] = int(size)

        try:
            if existing:
                file = self.updateFile(file)
            else:
                file = self.save(file)
            return file
        except ValidationException:
            if parentType == 'folder':
                Item().remove(item)
            raise

    def propagateSizeChange(self, item, sizeIncrement, updateItemSize=True):
        """
        Propagates a file size change (or file creation) to the necessary
        parents in the hierarchy. Internally, this records subtree size in
        the item, the parent folder, and the root node under which the item
        lives. Should be called anytime a new file is added, a file is
        deleted, or a file size changes.

        :param item: The parent item of the file.
        :type item: dict
        :param sizeIncrement: The change in size to propagate.
        :type sizeIncrement: int
        :param updateItemSize: Whether the item size should be updated. Set to
            False if you plan to delete the item immediately and don't care to
            update its size.
        """
        from .folder import Folder
        from .item import Item

        if updateItemSize:
            # Propagate size up to item
            Item().increment(query={
                '_id': item['_id']
            }, field='size', amount=sizeIncrement, multi=False)

        # Propagate size to direct parent folder
        Folder().increment(query={
            '_id': item['folderId']
        }, field='size', amount=sizeIncrement, multi=False)

        # Propagate size up to root data node
        ModelImporter.model(item['baseParentType']).increment(query={
            '_id': item['baseParentId']
        }, field='size', amount=sizeIncrement, multi=False)

    def createFile(self, creator, item, name, size, assetstore, mimeType=None,
                   saveFile=True, reuseExisting=False, assetstoreType=None):
        """
        Create a new file record in the database.

        :param item: The parent item.
        :param creator: The user creating the file.
        :param assetstore: The assetstore this file is stored in.
        :param name: The filename.
        :type name: str
        :param size: The size of the file in bytes.
        :type size: int
        :param mimeType: The mimeType of the file.
        :type mimeType: str
        :param saveFile: if False, don't save the file, just return it.
        :type saveFile: bool
        :param reuseExisting: If a file with the same name already exists in
            this location, return it rather than creating a new file.
        :type reuseExisting: bool
        :param assetstoreType: If a model other than assetstore will be used to
            initialize the assetstore adapter for this file, use this parameter to
            specify it. If it's a core model, pass its string name. If it's a plugin
            model, use a 2-tuple of the form (modelName, pluginName).
        :type assetstoreType: str or tuple
        """
        if reuseExisting:
            existing = self.findOne({
                'itemId': item['_id'],
                'name': name
            })
            if existing:
                return existing

        file = {
            'created': datetime.datetime.utcnow(),
            'creatorId': creator['_id'],
            'assetstoreId': assetstore['_id'],
            'name': name,
            'mimeType': mimeType,
            'size': size,
            'itemId': item['_id'] if item else None
        }

        if assetstoreType:
            file['assetstoreType'] = assetstoreType

        if saveFile:
            return self.save(file)
        return file

    def _propagateSizeToItem(self, event):
        """
        This callback updates an item's size to include that of a newly-created
        file.

        This generally should not be called or overridden directly. This should
        not be unregistered, as that would cause item, folder, and collection
        sizes to be inaccurate.
        """
        # This task is not performed in "createFile", in case
        # "saveFile==False". The item size should be updated only when it's
        # certain that the file will actually be saved. It is also possible for
        # "model.file.save" to set "defaultPrevented", which would prevent the
        # item from being saved initially.
        from .item import Item

        fileDoc = event.info
        itemId = fileDoc.get('itemId')
        if itemId and fileDoc.get('size'):
            item = Item().load(itemId, force=True)
            self.propagateSizeChange(item, fileDoc['size'])

    def updateFile(self, file):
        """
        Call this when changing properties of an existing file, such as name
        or MIME type. This causes the updated stamp to change, and also alerts
        the underlying assetstore adapter that file information has changed.
        """
        file['updated'] = datetime.datetime.utcnow()
        file = self.save(file)

        if file.get('assetstoreId'):
            self.getAssetstoreAdapter(file).fileUpdated(file)

        return file

    def getAssetstoreAdapter(self, file):
        """
        Return the assetstore adapter for the given file.  Return None if the
        file has no assetstore.
        """
        from girder.utility import assetstore_utilities

        if not file.get('assetstoreId'):
            return None
        assetstore = self._getAssetstoreModel(file).load(file['assetstoreId'])
        return assetstore_utilities.getAssetstoreAdapter(assetstore)

    def copyFile(self, srcFile, creator, item=None):
        """
        Copy a file so that we don't need to duplicate stored data.

        :param srcFile: The file to copy.
        :type srcFile: dict
        :param creator: The user copying the file.
        :param item: a new item to assign this file to (optional)
        :returns: a dict with the new file.
        """
        # Copy the source file's dictionary.  The individual assetstore
        # implementations will need to fix references if they cannot be
        # directly duplicated.
        file = srcFile.copy()
        # Immediately delete the original id so that we get a new one.
        del file['_id']
        file['copied'] = datetime.datetime.utcnow()
        file['copierId'] = creator['_id']
        if item:
            file['itemId'] = item['_id']
        if file.get('assetstoreId'):
            self.getAssetstoreAdapter(file).copyFile(srcFile, file)
        elif file.get('linkUrl'):
            file['linkUrl'] = srcFile['linkUrl']

        return self.save(file)

    def isOrphan(self, file):
        """
        Returns True if this file is orphaned (its item or attached entity is
        missing).

        :param file: The file to check.
        :type file: dict
        """
        if file.get('attachedToId'):
            attachedToType = file.get('attachedToType')
            if isinstance(attachedToType, six.string_types):
                modelType = ModelImporter.model(attachedToType)
            elif isinstance(attachedToType, list) and len(attachedToType) == 2:
                modelType = ModelImporter.model(*attachedToType)
            else:
                # Invalid 'attachedToType'
                return True
            if isinstance(modelType, (acl_mixin.AccessControlMixin,
                                      AccessControlledModel)):
                attachedDoc = modelType.load(
                    file.get('attachedToId'), force=True)
            else:
                attachedDoc = modelType.load(
                    file.get('attachedToId'))
        else:
            from .item import Item
            attachedDoc = Item().load(file.get('itemId'), force=True)
        return not attachedDoc

    def updateSize(self, file):
        """
        Returns the size of this file. Does not currently check the underlying
        assetstore to verify the size.

        :param file: The file.
        :type file: dict
        """
        # TODO: check underlying assetstore for size?
        return file.get('size', 0), 0

    def open(self, file):
        """
        Use this to expose a Girder file as a python file-like object. At the
        moment, this is a read-only interface, the equivalent of opening a
        system file with ``'rb'`` mode. This can also be used as a context
        manager, e.g.:

        >>> with File().open(file) as fh:
        >>>    while True:
        >>>        chunk = fh.read(CHUNK_LEN)
        >>>        if not chunk:
        >>>            break

        Using it this way will automatically close the file handle for you when
        the ``with`` block is left.

        :param file: A Girder file document.
        :type file: dict
        :return: A file-like object containing the bytes of the file.
        :rtype: girder.utility.abstract_assetstore_adapter.FileHandle
        """
        return self.getAssetstoreAdapter(file).open(file)

    def getGirderMountFilePath(self, file, validate=True):
        """
        If possible, get the path of the file on a local girder mount.

        :param file: The file document.
        :param validate: if True, check if the path exists and raise an
            exception if it does not.
        :returns: a girder mount path to the file or None if no such path is
            available.
        """
        mount = Setting().get(SettingKey.GIRDER_MOUNT_INFORMATION)
        if mount:
            path = mount['path'].rstrip('/') + path_util.getResourcePath('file', file, force=True)
            if not validate or os.path.exists(path):
                return path
        if validate:
            raise FilePathException("This file isn't accessible from a Girder mount.")

    def getLocalFilePath(self, file):
        """
        If an assetstore adapter supports it, return a path to the file on the
        local file system.

        :param file: The file document.
        :returns: a local path to the file or None if no such path is known.
        """
        adapter = self.getAssetstoreAdapter(file)
        try:
            return adapter.getLocalFilePath(file)
        except FilePathException as exc:
            try:
                return self.getGirderMountFilePath(file, True)
            except Exception:
                # If getting a Girder mount path throws, raise the original
                # exception
                pass
            raise exc
