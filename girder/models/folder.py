# -*- coding: utf-8 -*-
import copy
import datetime
import json
import os
import six

from bson.objectid import ObjectId
from .model_base import AccessControlledModel
from girder import events
from girder.constants import AccessType
from girder.exceptions import ValidationException, GirderException
from girder.utility.model_importer import ModelImporter
from girder.utility.progress import noProgress, setResponseTimeLimit


class Folder(AccessControlledModel):
    """
    Folders are used to store items and can also store other folders in
    a hierarchical way, like a directory on a filesystem. Every folder has
    its own set of access control policies, but by default the access
    control list is inherited from the folder's parent folder, if it has one.
    Top-level folders are ones whose parent is a user or a collection.
    """

    def initialize(self):
        self.name = 'folder'
        self.ensureIndices(('parentId', 'name', 'lowerName',
                            ([('parentId', 1), ('name', 1)], {})))
        self.ensureTextIndex({
            'name': 10,
            'description': 1
        })

        self.exposeFields(level=AccessType.READ, fields=(
            '_id', 'name', 'public', 'publicFlags', 'description', 'created', 'updated',
            'size', 'meta', 'parentId', 'parentCollection', 'creatorId',
            'baseParentType', 'baseParentId'))

    def validate(self, doc, allowRename=False):
        """
        Validate the name and description of the folder, ensure that it is
        associated with a valid parent and that it has a unique name.

        :param doc: the folder document to validate.
        :param allowRename: if True and a folder or item exists with the same
                            name, rename the folder so that it is unique.
        :returns: `the validated folder document`
        """
        from .item import Item

        doc['name'] = doc['name'].strip()
        doc['lowerName'] = doc['name'].lower()
        doc['description'] = doc['description'].strip()

        if not doc['name']:
            raise ValidationException('Folder name must not be empty.', 'name')

        if not doc['parentCollection'] in ('folder', 'user', 'collection'):
            # Internal error; this shouldn't happen
            raise GirderException('Invalid folder parent type: %s.' %
                                  doc['parentCollection'],
                                  'girder.models.folder.invalid-parent-type')
        name = doc['name']
        # If the folder already exists with the current name, don't check.
        # Although we don't want duplicate names, they can occur when there are
        # simultaneous uploads, and also because Mongo has no guaranteed
        # multi-collection uniqueness constraints.  If this occurs, and we are
        # changing a non-name property, don't validate the name (since that may
        # fail).  If the name is being changed, validate that it is probably
        # unique.
        checkName = '_id' not in doc or not self.findOne({'_id': doc['_id'], 'name': name})
        n = 0
        itemModel = Item()
        while checkName:
            q = {
                'parentId': doc['parentId'],
                'name': name,
                'parentCollection': doc['parentCollection']
            }
            if '_id' in doc:
                q['_id'] = {'$ne': doc['_id']}
            dupFolder = self.findOne(q, fields=['_id'])
            if doc['parentCollection'] == 'folder':
                q = {
                    'folderId': doc['parentId'],
                    'name': name
                }
                dupItem = itemModel.findOne(q, fields=['_id'])
            else:
                dupItem = None
            if dupItem is None and dupFolder is None:
                doc['name'] = name
                break
            if not allowRename:
                if dupFolder:
                    raise ValidationException('A folder with that name '
                                              'already exists here.', 'name')
                raise ValidationException('An item with that name already '
                                          'exists here.', 'name')
            n += 1
            name = '%s (%d)' % (doc['name'], n)
        return doc

    def load(self, id, level=AccessType.ADMIN, user=None, objectId=True,
             force=False, fields=None, exc=False):
        """
        We override load in order to ensure the folder has certain fields
        within it, and if not, we add them lazily at read time.

        :param id: The id of the resource.
        :type id: string or ObjectId
        :param user: The user to check access against.
        :type user: dict or None
        :param level: The required access type for the object.
        :type level: AccessType
        :param force: If you explicitly want to circumvent access
                      checking on this resource, set this to True.
        :type force: bool
        """
        # Ensure we include extra fields to do the migration below
        extraFields = {'baseParentId', 'baseParentType', 'parentId', 'parentCollection',
                       'name', 'lowerName'}
        loadFields = self._supplementFields(fields, extraFields)

        doc = super(Folder, self).load(
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

    def getSizeRecursive(self, folder):
        """
        Calculate the total size of the folder by recursing into all of its
        descendant folders.
        """
        size = folder['size']

        q = {
            'parentId': folder['_id'],
            'parentCollection': 'folder'
        }

        for child in self.find(q):
            size += self.getSizeRecursive(child)

        return size

    def setMetadata(self, folder, metadata, allowNull=False):
        """
        Set metadata on a folder.  A `ValidationException` is thrown in the
        cases where the metadata JSON object is badly formed, or if any of the
        metadata keys contains a period ('.').

        :param folder: The folder to set the metadata on.
        :type folder: dict
        :param metadata: A dictionary containing key-value pairs to add to
                     the folder's meta field
        :type metadata: dict
        :param allowNull: Whether to allow `null` values to be set in the item's
            metadata. If set to `False` or omitted, a `null` value will cause that
            metadata field to be deleted.
        :returns: the folder document
        """
        if 'meta' not in folder:
            folder['meta'] = {}

        # Add new metadata to existing metadata
        folder['meta'].update(six.viewitems(metadata))

        # Remove metadata fields that were set to null (use items in py3)
        if not allowNull:
            toDelete = [k for k, v in six.viewitems(metadata) if v is None]
            for key in toDelete:
                del folder['meta'][key]

        folder['updated'] = datetime.datetime.utcnow()

        self.validateKeys(folder['meta'])

        # Validate and save the item
        return self.save(folder)

    def deleteMetadata(self, folder, fields):
        """
        Delete metadata on a folder. A `ValidationException` is thrown if the
        metadata field names contain a period ('.') or begin with a dollar sign
        ('$').

        :param folder: The folder to delete metadata from.
        :type folder: dict
        :param fields: An array containing the field names to delete from the
            folder's meta field
        :type field: list
        :returns: the folder document
        """
        self.validateKeys(fields)

        if 'meta' not in folder:
            folder['meta'] = {}

        for field in fields:
            folder['meta'].pop(field, None)

        folder['updated'] = datetime.datetime.utcnow()

        return self.save(folder)

    def _updateDescendants(self, folderId, updateQuery):
        """
        This helper is used to update all items and folders underneath a
        folder. This is expensive, so think carefully before using it.

        :param folderId: The _id of the folder at the root of the subtree.
        :param updateQuery: The mongo query to apply to all of the children of
        the folder.
        :type updateQuery: dict
        """
        from .item import Item

        self.update(query={
            'parentId': folderId,
            'parentCollection': 'folder'
        }, update=updateQuery, multi=True)
        Item().update(query={
            'folderId': folderId,
        }, update=updateQuery, multi=True)

        q = {
            'parentId': folderId,
            'parentCollection': 'folder'
        }
        for child in self.find(q):
            self._updateDescendants(child['_id'], updateQuery)

    def _isAncestor(self, ancestor, descendant):
        """
        Returns whether folder "ancestor" is an ancestor of folder "descendant",
        or if they are the same folder.

        :param ancestor: The folder to test as an ancestor.
        :type ancestor: folder
        :param descendant: The folder to test as a descendant.
        :type descendant: folder
        """
        if ancestor['_id'] == descendant['_id']:
            return True

        if descendant['parentCollection'] != 'folder':
            return False

        descendant = self.load(descendant['parentId'], force=True)

        if descendant is None:
            return False

        return self._isAncestor(ancestor, descendant)

    def move(self, folder, parent, parentType):
        """
        Move the given folder from its current parent to another parent object.
        Raises an exception if folder is an ancestor of parent.

        :param folder: The folder to move.
        :type folder: dict
        :param parent: The new parent object.
        :param parentType: The type of the new parent object (user, collection,
                           or folder).
        :type parentType: str
        """
        if (parentType == 'folder' and (
                self._isAncestor(folder, parent) or folder['_id'] == parent['_id'])):
            raise ValidationException(
                'You may not move a folder underneath itself.')

        folder['parentId'] = parent['_id']
        folder['parentCollection'] = parentType

        if parentType == 'folder':
            rootType, rootId = parent['baseParentType'], parent['baseParentId']
        else:
            rootType, rootId = parentType, parent['_id']

        if (folder['baseParentType'], folder['baseParentId']) !=\
           (rootType, rootId):
            def propagateSizeChange(folder, inc):
                ModelImporter.model(folder['baseParentType']).increment(query={
                    '_id': folder['baseParentId']
                }, field='size', amount=inc, multi=False)

            totalSize = self.getSizeRecursive(folder)
            propagateSizeChange(folder, -totalSize)
            folder['baseParentType'] = rootType
            folder['baseParentId'] = rootId
            propagateSizeChange(folder, totalSize)
            self._updateDescendants(folder['_id'], {
                '$set': {
                    'baseParentType': rootType,
                    'baseParentId': rootId
                }
            })

        return self.save(folder)

    def clean(self, folder, progress=None, **kwargs):
        """
        Delete all contents underneath a folder recursively, but leave the
        folder itself.

        :param folder: The folder document to delete.
        :type folder: dict
        :param progress: A progress context to record progress on.
        :type progress: girder.utility.progress.ProgressContext or None.
        """
        from .item import Item

        setResponseTimeLimit()
        # Delete all child items
        itemModel = Item()
        items = itemModel.find({
            'folderId': folder['_id']
        })
        for item in items:
            setResponseTimeLimit()
            itemModel.remove(item, progress=progress, **kwargs)
            if progress:
                progress.update(increment=1, message='Deleted item %s' % item['name'])
        # subsequent operations take a long time, so free the cursor's resources
        items.close()

        # Delete all child folders
        folders = self.find({
            'parentId': folder['_id'],
            'parentCollection': 'folder'
        })
        for subfolder in folders:
            self.remove(subfolder, progress=progress, **kwargs)
        folders.close()

    def remove(self, folder, progress=None, **kwargs):
        """
        Delete a folder recursively.

        :param folder: The folder document to delete.
        :type folder: dict
        :param progress: A progress context to record progress on.
        :type progress: girder.utility.progress.ProgressContext or None.
        """
        # Remove the contents underneath this folder recursively.
        from .upload import Upload

        self.clean(folder, progress, **kwargs)

        # Delete pending uploads into this folder
        uploadModel = Upload()
        uploads = uploadModel.find({
            'parentId': folder['_id'],
            'parentType': 'folder'
        })
        for upload in uploads:
            uploadModel.remove(upload, progress=progress, **kwargs)
        uploads.close()

        # Delete this folder
        AccessControlledModel.remove(self, folder, progress=progress, **kwargs)
        if progress:
            progress.update(increment=1, message='Deleted folder %s' %
                            folder['name'])

    def childItems(self, folder, limit=0, offset=0, sort=None, filters=None,
                   **kwargs):
        """
        Generator function that yields child items in a folder.  Passes any
        kwargs to the find function.

        :param folder: The parent folder.
        :param limit: Result limit.
        :param offset: Result offset.
        :param sort: The sort structure to pass to pymongo.
        :param filters: Additional query operators.
        """
        from .item import Item

        q = {
            'folderId': folder['_id']
        }
        q.update(filters or {})

        return Item().find(q, limit=limit, offset=offset, sort=sort, **kwargs)

    def childFolders(self, parent, parentType, user=None, limit=0, offset=0,
                     sort=None, filters=None, **kwargs):
        """
        This generator will yield child folders of a user, collection, or
        folder, with access policy filtering.  Passes any kwargs to the find
        function.

        :param parent: The parent object.
        :type parentType: Type of the parent object.
        :param parentType: The parent type.
        :type parentType: 'user', 'folder', or 'collection'
        :param user: The user running the query. Only returns folders that this
                     user can see.
        :param limit: Result limit.
        :param offset: Result offset.
        :param sort: The sort structure to pass to pymongo.
        :param filters: Additional query operators.
        """
        if not filters:
            filters = {}

        parentType = parentType.lower()
        if parentType not in ('folder', 'user', 'collection'):
            raise ValidationException('The parentType must be folder, collection, or user.')

        q = {
            'parentId': parent['_id'],
            'parentCollection': parentType
        }
        q.update(filters)

        cursor = self.findWithPermissions(
            q, sort=sort, user=user, level=AccessType.READ, limit=limit, offset=offset, **kwargs)

        return iter(cursor)

    def createFolder(self, parent, name, description='', parentType='folder',
                     public=None, creator=None, allowRename=False, reuseExisting=False):
        """
        Create a new folder under the given parent.

        :param parent: The parent document. Should be a folder, user, or
                       collection.
        :type parent: dict
        :param name: The name of the folder.
        :type name: str
        :param description: Description for the folder.
        :type description: str
        :param parentType: What type the parent is:
                           ('folder' | 'user' | 'collection')
        :type parentType: str
        :param public: Public read access flag.
        :type public: bool or None to inherit from parent
        :param creator: User document representing the creator of this folder.
        :type creator: dict
        :param allowRename: if True and a folder or item of this name exists,
                            automatically rename the folder.
        :type allowRename: bool
        :param reuseExisting: If a folder with the given name already exists
            under the given parent, return that folder rather than creating a
            new one.
        :type reuseExisting: bool
        :returns: The folder document that was created.
        """
        if reuseExisting:
            existing = self.findOne({
                'parentId': parent['_id'],
                'name': name,
                'parentCollection': parentType
            })

            if existing:
                return existing

        parentType = parentType.lower()
        if parentType not in ('folder', 'user', 'collection'):
            raise ValidationException('The parentType must be folder, collection, or user.')

        if parentType == 'folder':
            if 'baseParentId' not in parent:
                pathFromRoot = self.parentsToRoot(
                    parent, user=creator, force=True)
                parent['baseParentId'] = pathFromRoot[0]['object']['_id']
                parent['baseParentType'] = pathFromRoot[0]['type']
        else:
            parent['baseParentId'] = parent['_id']
            parent['baseParentType'] = parentType

        now = datetime.datetime.utcnow()

        if creator is None:
            creatorId = None
        else:
            creatorId = creator.get('_id', None)

        folder = {
            'name': name,
            'description': description,
            'parentCollection': parentType,
            'baseParentId': parent['baseParentId'],
            'baseParentType': parent['baseParentType'],
            'parentId': ObjectId(parent['_id']),
            'creatorId': creatorId,
            'created': now,
            'updated': now,
            'size': 0,
            'meta': {}
        }

        if parentType in ('folder', 'collection'):
            self.copyAccessPolicies(src=parent, dest=folder, save=False)

        if creator is not None:
            self.setUserAccess(folder, user=creator, level=AccessType.ADMIN,
                               save=False)

        # Allow explicit public flag override if it's set.
        if public is not None and isinstance(public, bool):
            self.setPublic(folder, public, save=False)

        if allowRename:
            self.validate(folder, allowRename=True)

        # Now validate and save the folder.
        return self.save(folder)

    def updateFolder(self, folder):
        """
        Updates a folder.

        :param folder: The folder document to update
        :type folder: dict
        :returns: The folder document that was edited.
        """
        folder['updated'] = datetime.datetime.utcnow()

        # Validate and save the folder
        return self.save(folder)

    def filter(self, doc, user=None, additionalKeys=None):
        """
        Overrides the parent ``filter`` method to add an empty meta field
        (if it doesn't exist) to the returned folder.
        """
        filteredDoc = super(Folder, self).filter(doc, user, additionalKeys=additionalKeys)
        if 'meta' not in filteredDoc:
            filteredDoc['meta'] = {}

        return filteredDoc

    def parentsToRoot(self, folder, curPath=None, user=None, force=False, level=AccessType.READ):
        """
        Get the path to traverse to a root of the hierarchy.

        :param folder: The folder whose root to find
        :type folder: dict
        :returns: an ordered list of dictionaries from root to the current folder
        """
        curPath = curPath or []
        curParentId = folder['parentId']
        curParentType = folder['parentCollection']

        if curParentType in ('user', 'collection'):
            curParentObject = ModelImporter.model(curParentType).load(
                curParentId, user=user, level=level, force=force)

            if force:
                parentFiltered = curParentObject
            else:
                parentFiltered = ModelImporter.model(curParentType).filter(curParentObject, user)

            return [{
                'type': curParentType,
                'object': parentFiltered
            }] + curPath
        else:
            curParentObject = self.load(curParentId, user=user, level=level, force=force)
            curPath = [{
                'type': curParentType,
                'object': curParentObject if force else self.filter(curParentObject, user)
            }] + curPath

            return self.parentsToRoot(curParentObject, curPath, user=user, force=force)

    def countItems(self, folder):
        """
        Returns the number of items within the given folder.
        """
        return self.childItems(folder, fields=()).count()

    def countFolders(self, folder, user=None, level=None):
        """
        Returns the number of subfolders within the given folder. Access
        checking is optional; to circumvent access checks, pass ``level=None``.

        :param folder: The parent folder.
        :type folder: dict
        :param user: If performing access checks, the user to check against.
        :type user: dict or None
        :param level: The required access level, or None to return the raw
            subfolder count.
        """
        fields = () if level is None else ('access', 'public')

        folders = self.findWithPermissions({
            'parentId': folder['_id'],
            'parentCollection': 'folder'
        }, fields=fields, user=user, level=level)

        return folders.count()

    def subtreeCount(self, folder, includeItems=True, user=None, level=None):
        """
        Return the size of the subtree rooted at the given folder. Includes
        the root folder in the count.

        :param folder: The root of the subtree.
        :type folder: dict
        :param includeItems: Whether to include items in the subtree count, or
            just folders.
        :type includeItems: bool
        :param user: If filtering by permission, the user to filter against.
        :param level: If filtering by permission, the required permission level.
        :type level: AccessLevel
        """
        count = 1

        if includeItems:
            count += self.countItems(folder)

        folders = self.findWithPermissions({
            'parentId': folder['_id'],
            'parentCollection': 'folder'
        }, fields='access', user=user, level=level)

        count += sum(self.subtreeCount(subfolder, includeItems=includeItems,
                                       user=user, level=level)
                     for subfolder in folders)

        return count

    def fileList(self, doc, user=None, path='', includeMetadata=False,
                 subpath=True, mimeFilter=None, data=True):
        """
        This function generates a list of 2-tuples whose first element is the
        relative path to the file from the folder's root and whose second
        element depends on the value of the `data` flag. If `data=True`, the
        second element will be a generator that will generate the bytes of the
        file data as stored in the assetstore. If `data=False`, the second
        element is the file document itself.

        :param doc: The folder to list.
        :param user: The user used for access.
        :param path: A path prefix to add to the results.
        :type path: str
        :param includeMetadata: if True and there is any metadata, include a
                                result which is the JSON string of the
                                metadata.  This is given a name of
                                metadata[-(number).json that is distinct from
                                any file within the folder.
        :type includeMetadata: bool
        :param subpath: if True, add the folder's name to the path.
        :type subpath: bool
        :param mimeFilter: Optional list of MIME types to filter by. Set to
            None to include all files.
        :type mimeFilter: `list or tuple`
        :param data: If True return raw content of each file as stored in the
            assetstore, otherwise return file document.
        :type data: bool
        :returns: Iterable over files in this folder, where each element is a
                  tuple of (path name of the file, stream function with file
                  data or file object).
        :rtype: generator(str, func)
        """
        from .item import Item

        itemModel = Item()
        if subpath:
            path = os.path.join(path, doc['name'])
        metadataFile = 'girder-folder-metadata.json'

        # Eagerly evaluate this list, as the MongoDB cursor can time out on long requests
        childFolders = list(self.childFolders(
            parentType='folder', parent=doc, user=user,
            fields=['name'] + (['meta'] if includeMetadata else [])
        ))
        for sub in childFolders:
            if sub['name'] == metadataFile:
                metadataFile = None
            for (filepath, file) in self.fileList(
                    sub, user, path, includeMetadata, subpath=True,
                    mimeFilter=mimeFilter, data=data):
                yield (filepath, file)

        # Eagerly evaluate this list, as the MongoDB cursor can time out on long requests
        childItems = list(self.childItems(
            folder=doc, fields=['name'] + (['meta'] if includeMetadata else [])
        ))
        for item in childItems:
            if item['name'] == metadataFile:
                metadataFile = None
            for (filepath, file) in itemModel.fileList(
                    item, user, path, includeMetadata, mimeFilter=mimeFilter, data=data):
                yield (filepath, file)

        if includeMetadata and metadataFile and doc.get('meta', {}):
            def stream():
                yield json.dumps(doc['meta'], default=str)
            yield (os.path.join(path, metadataFile), stream)

    def copyFolder(self, srcFolder, parent=None, name=None, description=None,
                   parentType=None, public=None, creator=None, progress=None,
                   firstFolder=None):
        """
        Copy a folder, including all child items and child folders.

        :param srcFolder: the folder to copy.
        :type srcFolder: dict
        :param parent: The parent document.  Must be a folder, user, or
                       collection.
        :type parent: dict
        :param name: The name of the new folder.  None to copy the original
                     name.
        :type name: str
        :param description: Description for the new folder.  None to copy the
                            original description.
        :type description: str
        :param parentType: What type the parent is:
                           ('folder' | 'user' | 'collection')
        :type parentType: str
        :param public: Public read access flag.  None to inherit from parent,
                       'original' to inherit from original folder.
        :type public: bool, None, or 'original'.
        :param creator: user representing the creator of the new folder.
        :type creator: dict
        :param progress: a progress context to record process on.
        :type progress: girder.utility.progress.ProgressContext or None.
        :param firstFolder: if not None, the first folder copied in a tree of
                            folders.
        :returns: the new folder document.
        """
        setResponseTimeLimit()
        if parentType is None:
            parentType = srcFolder['parentCollection']
        parentType = parentType.lower()
        if parentType not in ('folder', 'user', 'collection'):
            raise ValidationException('The parentType must be folder, '
                                      'collection, or user.')
        if parent is None:
            parent = ModelImporter.model(parentType).load(srcFolder['parentId'], force=True)
        if name is None:
            name = srcFolder['name']
        if description is None:
            description = srcFolder['description']
        if public is not None and isinstance(public, str):
            if public == 'original':
                public = srcFolder.get('public', None)
            else:
                public = public == 'true'
        newFolder = self.createFolder(
            parentType=parentType, parent=parent, name=name,
            description=description, public=public, creator=creator,
            allowRename=True)
        if firstFolder is None:
            firstFolder = newFolder
        return self.copyFolderComponents(
            srcFolder, newFolder, creator, progress, firstFolder)

    def copyFolderComponents(self, srcFolder, newFolder, creator, progress,
                             firstFolder=None):
        """
        Copy the items, subfolders, and extended data of a folder that was just
        copied.

        :param srcFolder: the original folder.
        :type srcFolder: dict
        :param newFolder: the new folder.
        :type newFolder: dict
        :param creator: user representing the creator of the new folder.
        :type creator: dict
        :param progress: a progress context to record process on.
        :type progress: girder.utility.progress.ProgressContext or None.
        :param firstFolder: if not None, the first folder copied in a tree of
                            folders.
        :returns: the new folder document.
        """
        from .item import Item

        # copy metadata and other extension values
        if 'meta' in srcFolder:
            newFolder['meta'] = copy.deepcopy(srcFolder['meta'])
        filteredFolder = self.filter(newFolder, creator)
        for key in srcFolder:
            if key not in filteredFolder and key not in newFolder:
                newFolder[key] = copy.deepcopy(srcFolder[key])
        newFolder = self.save(newFolder, triggerEvents=False)
        # Give listeners a chance to change things
        events.trigger('model.folder.copy.prepare', (srcFolder, newFolder))
        # copy items
        itemModel = Item()
        for item in self.childItems(folder=srcFolder):
            setResponseTimeLimit()
            itemModel.copyItem(item, creator, folder=newFolder)
            if progress:
                progress.update(increment=1, message='Copied item ' + item['name'])
        # copy subfolders
        for sub in self.childFolders(parentType='folder', parent=srcFolder, user=creator):
            if firstFolder and firstFolder['_id'] == sub['_id']:
                continue
            self.copyFolder(sub, parent=newFolder, parentType='folder',
                            creator=creator, progress=progress)
        events.trigger('model.folder.copy.after', newFolder)
        if progress:
            progress.update(increment=1, message='Copied folder ' + newFolder['name'])

        # Reload to get updated size value
        return self.load(newFolder['_id'], force=True)

    def setAccessList(self, doc, access, save=False, recurse=False, user=None,
                      progress=noProgress, setPublic=None, publicFlags=None, force=False):
        """
        Overrides AccessControlledModel.setAccessList to add a recursive
        option. When `recurse=True`, this will set the access list on all
        subfolders to which the given user has ADMIN access level. Any
        subfolders that the given user does not have ADMIN access on will be
        skipped.

        :param doc: The folder to set access settings on.
        :type doc: girder.models.folder
        :param access: The access control list.
        :type access: dict
        :param save: Whether the changes should be saved to the database.
        :type save: bool
        :param recurse: Whether this access list should be propagated to all
            subfolders underneath this folder.
        :type recurse: bool
        :param user: The current user (for recursive mode filtering).
        :param progress: Progress context to update.
        :type progress: :py:class:`girder.utility.progress.ProgressContext`
        :param setPublic: Pass this if you wish to set the public flag on the
            resources being updated.
        :type setPublic: bool or None
        :param publicFlags: Pass this if you wish to set the public flag list on
            resources being updated.
        :type publicFlags: flag identifier str, or list/set/tuple of them, or None
        :param force: Set this to True to set the flags regardless of the passed in
            user's permissions.
        :type force: bool
        """
        progress.update(increment=1, message='Updating ' + doc['name'])
        if setPublic is not None:
            self.setPublic(doc, setPublic, save=False)

        if publicFlags is not None:
            doc = self.setPublicFlags(doc, publicFlags, user=user, save=False, force=force)

        doc = AccessControlledModel.setAccessList(
            self, doc, access, user=user, save=save, force=force)

        if recurse:
            subfolders = self.findWithPermissions({
                'parentId': doc['_id'],
                'parentCollection': 'folder'
            }, user=user, level=AccessType.ADMIN)

            for folder in subfolders:
                self.setAccessList(
                    folder, access, save=True, recurse=True, user=user,
                    progress=progress, setPublic=setPublic, publicFlags=publicFlags, force=force)

        return doc

    def isOrphan(self, folder):
        """
        Returns True if this folder is orphaned (its parent is missing).

        :param folder: The folder to check.
        :type folder: dict
        """
        return not ModelImporter.model(folder.get('parentCollection')).load(
            folder.get('parentId'), force=True)

    def updateSize(self, doc):
        """
        Recursively recomputes the size of this folder and its underlying
        folders and fixes the sizes as needed.

        :param doc: The folder.
        :type doc: dict
        """
        from .item import Item

        size = 0
        fixes = 0
        # recursively fix child folders but don't include their size
        children = self.find({
            'parentId': doc['_id'],
            'parentCollection': 'folder'
        })
        for child in children:
            _, f = self.updateSize(child)
            fixes += f
        # get correct size from child items
        itemModel = Item()
        for item in self.childItems(doc):
            s, f = itemModel.updateSize(item)
            size += s
            fixes += f
        # fix value if incorrect
        if size != doc.get('size'):
            self.update({'_id': doc['_id']}, update={'$set': {'size': size}})
            fixes += 1
        return size, fixes
