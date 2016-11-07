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
import datetime
import six

from .model_base import Model, ValidationException
from girder import events
from girder.constants import AccessType, CoreEventHandler
from girder.models.model_base import AccessControlledModel
from girder.utility import assetstore_utilities, acl_mixin


class File(acl_mixin.AccessControlMixin, Model):
    """
    This model represents a File, which is stored in an assetstore.
    """
    def initialize(self):
        self.name = 'file'
        self.ensureIndices(
            ['itemId', 'assetstoreId', 'exts'] +
            assetstore_utilities.fileIndexFields())
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
        if file.get('assetstoreId'):
            self.getAssetstoreAdapter(file).deleteFile(file)

        if file['itemId']:
            item = self.model('item').load(file['itemId'], force=True)
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
        if file.get('assetstoreId'):
            return self.getAssetstoreAdapter(file).downloadFile(
                file, offset=offset, headers=headers, endByte=endByte,
                contentDisposition=contentDisposition,
                extraParameters=extraParameters)
        elif file.get('linkUrl'):
            if headers:
                raise cherrypy.HTTPRedirect(file['linkUrl'])
            else:
                endByte = endByte or len(file['linkUrl'])

                def stream():
                    yield file['linkUrl'][offset:endByte]
                return stream
        else:  # pragma: no cover
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
        if 'name' not in doc or not doc['name']:
            raise ValidationException('File name must not be empty.', 'name')

        doc['exts'] = [ext.lower() for ext in doc['name'].split('.')[1:]]

        return doc

    def createLinkFile(self, name, parent, parentType, url, creator, size=None, mimeType=None):
        """
        Create a file that is a link to a URL, rather than something we maintain
        in an assetstore.

        :param name: The local name for the file.
        :type name: str
        :param parent: The parent object for this file.
        :type parent: folder or item
        :param parentType: The parent type (folder or item)
        :type parentType: str
        :param url: The URL that this file points to
        :param creator: The user creating the file.
        :type creator: dict
        :param size: The size of the file in bytes. (optional)
        :type size: int
        :param mimeType: The mimeType of the file. (optional)
        :type mimeType: str
        """
        if parentType == 'folder':
            # Create a new item with the name of the file.
            item = self.model('item').createItem(
                name=name, creator=creator, folder=parent)
        elif parentType == 'item':
            item = parent

        file = {
            'created': datetime.datetime.utcnow(),
            'itemId': item['_id'],
            'creatorId': creator['_id'],
            'assetstoreId': None,
            'name': name,
            'mimeType': mimeType,
            'linkUrl': url
        }

        if size is not None:
            file['size'] = int(size)

        try:
            file = self.save(file)
            return file
        except ValidationException:
            if parentType == 'folder':
                self.model('item').remove(item)
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
        if updateItemSize:
            # Propagate size up to item
            self.model('item').increment(query={
                '_id': item['_id']
            }, field='size', amount=sizeIncrement, multi=False)

        # Propagate size to direct parent folder
        self.model('folder').increment(query={
            '_id': item['folderId']
        }, field='size', amount=sizeIncrement, multi=False)

        # Propagate size up to root data node
        self.model(item['baseParentType']).increment(query={
            '_id': item['baseParentId']
        }, field='size', amount=sizeIncrement, multi=False)

    def createFile(self, creator, item, name, size, assetstore, mimeType=None,
                   saveFile=True, reuseExisting=False):
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
        fileDoc = event.info
        itemId = fileDoc.get('itemId')
        if itemId and fileDoc.get('size'):
            item = self.model('item').load(itemId, force=True)
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
        Return the assetstore adapter for the given file.
        """
        assetstore = self.model('assetstore').load(file['assetstoreId'])
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
                modelType = self.model(attachedToType)
            elif isinstance(attachedToType, list) and len(attachedToType) == 2:
                modelType = self.model(*attachedToType)
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
            attachedDoc = self.model('item').load(
                file.get('itemId'), force=True)
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
