import copy
import datetime
import json
import logging
import os

from bson.objectid import ObjectId
from .model_base import Model
from girder import events
from girder.constants import AccessType
from girder.exceptions import ValidationException, GirderException
from girder.utility import acl_mixin
from girder.utility.model_importer import ModelImporter

logger = logging.getLogger(__name__)


class Item(acl_mixin.AccessControlMixin, Model):
    """
    Items are leaves in the data hierarchy. They can contain 0 or more
    files within them, and can also contain arbitrary metadata.
    """

    def initialize(self):
        self.name = 'item'
        self.ensureIndices(('folderId', 'name', 'lowerName',
                            ([('folderId', 1), ('name', 1)], {})))
        self.ensureTextIndex({
            'name': 10,
            'description': 1
        })
        self.resourceColl = 'folder'
        self.resourceParent = 'folderId'

        self.exposeFields(level=AccessType.READ, fields=(
            '_id', 'size', 'updated', 'description', 'created', 'meta',
            'creatorId', 'folderId', 'name', 'baseParentType', 'baseParentId',
            'copyOfItem'))

    def _validateString(self, value):
        """
        Make sure a value is a string and is stripped of whitespace.

        :param value: the value to coerce into a string if it isn't already.
        :returns: the string version of the value.
        """
        if value is None:
            value = ''
        if not isinstance(value, str):
            value = str(value)
        return value.strip()

    def validate(self, doc):
        from .folder import Folder

        doc['name'] = self._validateString(doc.get('name', ''))
        doc['description'] = self._validateString(doc.get('description', ''))

        if not doc['name']:
            raise ValidationException('Item name must not be empty.', 'name')

        # Ensure unique name among sibling items and folders. If the desired
        # name collides with an existing item or folder, we will append (n)
        # onto the end of the name, incrementing n until the name is unique.
        name = doc['name']
        # If the item already exists with the current name, don't check.
        # Although we don't want duplicate names, they can occur when there are
        # simultaneous uploads, and also because Mongo has no guaranteed
        # multi-collection uniqueness constraints.  If this occurs, and we are
        # changing a non-name property, don't validate the name (since that may
        # fail).  If the name is being changed, validate that it is probably
        # unique.
        checkName = '_id' not in doc or not self.findOne({'_id': doc['_id'], 'name': name})
        n = 0
        while checkName:
            q = {
                'name': name,
                'folderId': doc['folderId']
            }
            if '_id' in doc:
                q['_id'] = {'$ne': doc['_id']}
            dupItem = self.findOne(q, fields=['_id'])

            q = {
                'parentId': doc['folderId'],
                'name': name,
                'parentCollection': 'folder'
            }
            dupFolder = Folder().findOne(q, fields=['_id'])
            if dupItem is None and dupFolder is None:
                doc['name'] = name
                checkName = False
            else:
                n += 1
                name = '%s (%d)' % (doc['name'], n)

        doc['lowerName'] = doc['name'].lower()
        return doc

    def load(self, id, level=AccessType.ADMIN, user=None, objectId=True,
             force=False, fields=None, exc=False):
        """
        Calls AccessControlMixin.load while doing some auto-correction.

        Takes the same parameters as
        :py:func:`girder.models.model_base.AccessControlMixin.load`.
        """
        # Ensure we include extra fields to do the migration below
        extraFields = {'baseParentId', 'baseParentType', 'parentId', 'parentCollection', 'meta',
                       'name', 'lowerName'}
        loadFields = self._supplementFields(fields, extraFields)

        doc = super().load(
            id=id, level=level, user=user, objectId=objectId, force=force, fields=loadFields,
            exc=exc)

        if doc is not None:
            if 'baseParentType' not in doc:
                pathFromRoot = self.parentsToRoot(doc, user=user, force=True)
                baseParent = pathFromRoot[0]
                doc['baseParentId'] = baseParent['object']['_id']
                doc['baseParentType'] = baseParent['type']
                self.update({'_id': doc['_id']}, {'$set': {
                    'baseParentId': doc['baseParentId'],
                    'baseParentType': doc['baseParentType']
                }})
            if 'lowerName' not in doc:
                doc['lowerName'] = doc['name'].lower()
                self.update({'_id': doc['_id']}, {'$set': {
                    'lowerName': doc['lowerName']
                }})
            if 'meta' not in doc:
                doc['meta'] = {}
                self.update({'_id': doc['_id']}, {'$set': {
                    'meta': {}
                }})

            self._removeSupplementalFields(doc, fields)

        return doc

    def move(self, item, folder):
        """
        Move the given item from its current folder into another folder.

        :param item: The item to move.
        :type item: dict
        :param folder: The folder to move the item into.
        :type folder: dict.
        """
        self.propagateSizeChange(item, -item['size'])

        item['folderId'] = folder['_id']
        item['baseParentType'] = folder['baseParentType']
        item['baseParentId'] = folder['baseParentId']

        self.propagateSizeChange(item, item['size'])

        return self.save(item)

    def propagateSizeChange(self, item, inc):
        from .folder import Folder

        Folder().increment(query={
            '_id': item['folderId']
        }, field='size', amount=inc, multi=False)

        ModelImporter.model(item['baseParentType']).increment(query={
            '_id': item['baseParentId']
        }, field='size', amount=inc, multi=False)

    def recalculateSize(self, item):
        """
        Recalculate the item size based on the files that are in it.  If this
        is different than the recorded size, propagate the changes.
        :param item: The item to recalculate the size of.
        :returns: the recalculated size in bytes
        """
        size = 0
        for file in self.childFiles(item):
            # We could add a recalculateSize to the file model, in which case
            # this would be:
            # size += File().recalculateSize(file)
            size += file.get('size', 0)
        delta = size - item.get('size', 0)
        if delta:
            logger.info(
                'Item %s was wrong size: was %d, is %d',
                item['_id'], item['size'], size
            )
            item['size'] = size
            self.update({'_id': item['_id']}, update={'$set': {'size': size}})
            self.propagateSizeChange(item, delta)
        return size

    def childFiles(self, item, limit=0, offset=0, sort=None, **kwargs):
        """
        Returns child files of the item.  Passes any kwargs to the find
        function.

        :param item: The parent item.
        :param limit: Result limit.
        :param offset: Result offset.
        :param sort: The sort structure to pass to pymongo.
        """
        from .file import File
        q = {
            'itemId': item['_id']
        }

        return File().find(q, limit=limit, offset=offset, sort=sort, **kwargs)

    def remove(self, item, **kwargs):
        """
        Delete an item, and all references to it in the database.

        :param item: The item document to delete.
        :type item: dict
        """
        from .file import File
        from .upload import Upload

        # Delete all files in this item
        fileModel = File()
        files = fileModel.find({
            'itemId': item['_id']
        })
        for file in files:
            fileKwargs = kwargs.copy()
            fileKwargs.pop('updateItemSize', None)
            fileModel.remove(file, updateItemSize=False, **fileKwargs)

        # Delete pending uploads into this item
        uploadModel = Upload()
        uploads = uploadModel.find({
            'parentId': item['_id'],
            'parentType': 'item'
        })
        for upload in uploads:
            uploadModel.remove(upload, **kwargs)

        # Delete the item itself
        super().remove(item)

    def createItem(self, name, creator, folder, description='',
                   reuseExisting=False):
        """
        Create a new item. The creator will be given admin access to it.

        :param name: The name of the item.
        :type name: str
        :param description: Description for the item.
        :type description: str
        :param folder: The parent folder of the item.
        :param creator: User document representing the creator of the item.
        :type creator: dict
        :param reuseExisting: If an item with the given name already exists
            under the given folder, return that item rather than creating a
            new one.
        :type reuseExisting: bool
        :returns: The item document that was created.
        """
        if reuseExisting:
            existing = self.findOne({
                'folderId': folder['_id'],
                'name': name
            })
            if existing:
                return existing

        now = datetime.datetime.now(datetime.timezone.utc)

        if not isinstance(creator, dict) or '_id' not in creator:
            # Internal error -- this shouldn't be called without a user.
            raise GirderException('Creator must be a user.',
                                  'girder.models.item.creator-not-user')

        if 'baseParentType' not in folder:
            pathFromRoot = self.parentsToRoot({'folderId': folder['_id']},
                                              creator, force=True)
            folder['baseParentType'] = pathFromRoot[0]['type']
            folder['baseParentId'] = pathFromRoot[0]['object']['_id']

        return self.save({
            'name': self._validateString(name),
            'description': self._validateString(description),
            'folderId': ObjectId(folder['_id']),
            'creatorId': creator['_id'],
            'baseParentType': folder['baseParentType'],
            'baseParentId': folder['baseParentId'],
            'created': now,
            'updated': now,
            'size': 0,
            'meta': {}
        })

    def updateItem(self, item):
        """
        Updates an item.

        :param item: The item document to update
        :type item: dict
        :returns: The item document that was edited.
        """
        item['updated'] = datetime.datetime.now(datetime.timezone.utc)

        # Validate and save the item
        return self.save(item)

    def filter(self, doc, user=None, additionalKeys=None):
        """
        Overrides the parent ``filter`` method to add an empty meta field
        (if it doesn't exist) to the returned folder.
        """
        filteredDoc = super().filter(doc, user, additionalKeys=additionalKeys)
        if 'meta' not in filteredDoc:
            filteredDoc['meta'] = {}

        return filteredDoc

    def setMetadata(self, item, metadata, allowNull=False):
        """
        Set metadata on an item.  A `ValidationException` is thrown in the
        cases where the metadata JSON object is badly formed, or if any of the
        metadata keys contains a period ('.').

        :param item: The item to set the metadata on.
        :type item: dict
        :param metadata: A dictionary containing key-value pairs to add to
                     the items meta field
        :type metadata: dict
        :param allowNull: Whether to allow `null` values to be set in the item's
                     metadata. If set to `False` or omitted, a `null` value will cause that
                     metadata field to be deleted.
        :returns: the item document
        """
        if 'meta' not in item:
            item['meta'] = {}

        # Add new metadata to existing metadata
        item['meta'].update(metadata.items())

        # Remove metadata fields that were set to null (use items in py3)
        if not allowNull:
            toDelete = [k for k, v in metadata.items() if v is None]
            for key in toDelete:
                del item['meta'][key]

        self.validateKeys(item['meta'])

        item['updated'] = datetime.datetime.now(datetime.timezone.utc)

        # Validate and save the item
        return self.save(item)

    def deleteMetadata(self, item, fields):
        """
        Delete metadata on an item. A `ValidationException` is thrown if the
        metadata field names contain a period ('.') or begin with a dollar sign
        ('$').

        :param item: The item to delete metadata from.
        :type item: dict
        :param fields: An array containing the field names to delete from the
            item's meta field
        :type field: list
        :returns: the item document
        """
        self.validateKeys(fields)

        if 'meta' not in item:
            item['meta'] = {}

        for field in fields:
            item['meta'].pop(field, None)

        item['updated'] = datetime.datetime.now(datetime.timezone.utc)

        return self.save(item)

    def parentsToRoot(self, item, user=None, force=False):
        """
        Get the path to traverse to a root of the hierarchy.

        :param item: The item whose root to find
        :type item: dict
        :param user: The user making the request (not required if force=True).
        :type user: dict or None
        :param force: Set to True to skip permission checking. If False, the
            returned models will be filtered.
        :type force: bool
        :returns: an ordered list of dictionaries from root to the current item
        """
        from .folder import Folder

        folderModel = Folder()
        curFolder = folderModel.load(
            item['folderId'], user=user, level=AccessType.READ, force=force)
        folderIdsToRoot = folderModel.parentsToRoot(
            curFolder, user=user, level=AccessType.READ, force=force)

        if force:
            folderIdsToRoot.append({'type': 'folder', 'object': curFolder})
        else:
            filteredFolder = folderModel.filter(curFolder, user)
            folderIdsToRoot.append({'type': 'folder', 'object': filteredFolder})

        return folderIdsToRoot

    def copyItem(self, srcItem, creator, name=None, folder=None, description=None):
        """
        Copy an item, including duplicating files and metadata.

        :param srcItem: the item to copy.
        :type srcItem: dict
        :param creator: the user who will own the copied item.
        :param name: The name of the new item.  None to copy the original name.
        :type name: str
        :param folder: The parent folder of the new item.  None to store in the
                same folder as the original item.
        :param description: Description for the new item.  None to copy the
                original description.
        :type description: str
        :returns: the new item.
        """
        from .file import File
        from .folder import Folder

        if name is None:
            name = srcItem['name']
        if folder is None:
            folder = Folder().load(srcItem['folderId'], force=True)
        if description is None:
            description = srcItem['description']
        newItem = self.createItem(
            folder=folder, name=name, creator=creator, description=description)
        # copy metadata and other extension values
        if 'meta' in srcItem:
            newItem['meta'] = copy.deepcopy(srcItem['meta'])
        filteredItem = self.filter(newItem, creator)
        for key in srcItem:
            if key not in filteredItem and key not in newItem:
                newItem[key] = copy.deepcopy(srcItem[key])
        # add a reference to the original item
        newItem['copyOfItem'] = srcItem['_id']
        newItem = self.save(newItem, triggerEvents=False)

        # Give listeners a chance to change things
        events.trigger('model.item.copy.prepare', (srcItem, newItem))
        # copy files
        fileModel = File()
        for file in self.childFiles(item=srcItem):
            fileModel.copyFile(file, creator=creator, item=newItem)

        # Reload to get updated size value
        newItem = self.load(newItem['_id'], force=True)
        events.trigger('model.item.copy.after', newItem)
        return newItem

    def fileList(self, doc, user=None, path='', includeMetadata=False,
                 subpath=True, mimeFilter=None, data=True):
        """
        This function generates a list of 2-tuples whose first element is the
        relative path to the file from the item's root and whose second
        element depends on the value of the `data` flag. If `data=True`, the
        second element will be a generator that will generate the bytes of the
        file data as stored in the assetstore. If `data=False`, the second
        element will be the file document itself.

        :param doc: The item to list.
        :param user: A user used to validate data that is returned.  This isn't
                     used, but is present to be consistent across all model
                     implementations of fileList.
        :param path: A path prefix to add to the results.
        :type path: str
        :param includeMetadata: If True and there is any metadata, include a
                                result which is the JSON string of the
                                metadata.  This is given a name of
                                metadata[-(number).json that is distinct from
                                any file within the item.
        :type includeMetadata: bool
        :param subpath: If True and the item has more than one file, any
                        metadata, or the sole file is not named the same as the
                        item, then the returned paths include the item name.
        :type subpath: bool
        :param mimeFilter: Optional list of MIME types to filter by. Set to
            None to include all files.
        :type mimeFilter: `list or tuple`
        :param data: If True return raw content of each file as stored in the
            assetstore, otherwise return file document.
        :type data: bool
        :returns: Iterable over files in this item, where each element is a
                  tuple of (path name of the file, stream function with file
                  data or file object).
        :rtype: generator(str, func)
        """
        from .file import File

        if subpath:
            files = list(self.childFiles(item=doc, limit=2))
            if (len(files) != 1 or files[0]['name'] != doc['name']
                    or (includeMetadata and doc.get('meta', {}))):
                path = os.path.join(path, doc['name'])
        metadataFile = 'girder-item-metadata.json'

        fileModel = File()
        # Eagerly evaluate this list, as the MongoDB cursor can time out on long requests
        # Don't use a "filter" projection here, since returning the full file document is promised
        # by this function, and file objects tend to not have large fields present
        childFiles = list(self.childFiles(item=doc))
        for file in childFiles:
            if not self._mimeFilter(file, mimeFilter):
                continue
            if file['name'] == metadataFile:
                metadataFile = None
            if data:
                val = fileModel.download(file, headers=False)
            else:
                val = file
            yield (os.path.join(path, file['name']), val)
        if includeMetadata and metadataFile and len(doc.get('meta', {})):
            def stream():
                yield json.dumps(doc['meta'], default=str)
            yield (os.path.join(path, metadataFile), stream)

    def _mimeFilter(self, file, mimeFilter):
        """
        Returns whether or not the given file should be passed through the given
        MIME filter. If no MIME filter is specified, all files are allowed.
        """
        if not mimeFilter:
            return True
        return file['mimeType'] in mimeFilter

    def isOrphan(self, item):
        """
        Returns True if this item is orphaned (its folder is missing).

        :param item: The item to check.
        :type item: dict
        """
        from .folder import Folder
        return not Folder().load(item.get('folderId'), force=True)

    def updateSize(self, doc):
        """
        Recomputes the size of this item and its underlying
        files and fixes the sizes as needed.

        :param doc: The item.
        :type doc: dict
        """
        from .file import File
        # get correct size from child files
        size = 0
        fixes = 0
        fileModel = File()
        for file in self.childFiles(doc):
            s, f = fileModel.updateSize(file)
            size += s
            fixes += f
        # fix value if incorrect
        if size != doc.get('size'):
            self.update({'_id': doc['_id']}, update={'$set': {'size': size}})
            fixes += 1
        return size, fixes
