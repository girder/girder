# -*- coding: utf-8 -*-
import datetime
import os

from .model_base import AccessControlledModel
from girder.constants import AccessType
from girder.exceptions import ValidationException
from girder.settings import SettingKey
from girder.utility.progress import noProgress


class Collection(AccessControlledModel):
    """
    Collections are the top level roots of the data hierarchy. They are used
    to group and organize data that is meant to be shared amongst users.
    """

    def initialize(self):
        self.name = 'collection'
        self.ensureIndices(['name'])
        self.ensureTextIndex({
            'name': 10,
            'description': 1
        })

        self.exposeFields(level=AccessType.READ, fields={
            '_id',
            'name',
            'description',
            'public',
            'publicFlags',
            'created',
            'updated',
            'size',
            'meta'
            })

    def validate(self, doc):
        doc['name'] = doc['name'].strip()
        if doc['description']:
            doc['description'] = doc['description'].strip()

        if not doc['name']:
            raise ValidationException(
                'Collection name must not be empty.', 'name')

        # Ensure unique name for the collection
        q = {
            'name': doc['name']
        }
        if '_id' in doc:
            q['_id'] = {'$ne': doc['_id']}
        duplicate = self.findOne(q, fields=['_id'])
        if duplicate is not None:
            raise ValidationException('A collection with that name already '
                                      'exists.', 'name')

        doc['lowerName'] = doc['name'].lower()

        return doc

    def remove(self, collection, progress=None, **kwargs):
        """
        Delete a collection recursively.

        :param collection: The collection document to delete.
        :type collection: dict
        :param progress: A progress context to record progress on.
        :type progress: girder.utility.progress.ProgressContext or None.
        """
        from .folder import Folder

        folderModel = Folder()
        folders = folderModel.find({
            'parentId': collection['_id'],
            'parentCollection': 'collection'
        })
        for folder in folders:
            folderModel.remove(folder, progress=progress, **kwargs)

        # Delete this collection
        super().remove(collection)
        if progress:
            progress.update(increment=1, message='Deleted collection ' + collection['name'])

    def createCollection(self, name, creator=None, description='', public=True,
                         reuseExisting=False):
        """
        Create a new collection.

        :param name: The name of the collection. Must be unique.
        :type name: str
        :param description: Description for the collection.
        :type description: str
        :param public: Public read access flag.
        :type public: bool
        :param creator: The user who is creating this collection.
        :type creator: dict
        :param reuseExisting: If a collection with the given name already exists
            return that collection rather than creating a new one.
        :type reuseExisting: bool
        :returns: The collection document that was created.
        """
        if reuseExisting:
            existing = self.findOne({
                'name': name
            })
            if existing:
                return existing

        now = datetime.datetime.utcnow()

        collection = {
            'name': name,
            'description': description,
            'creatorId': creator['_id'] if creator else None,
            'created': now,
            'updated': now,
            'size': 0,
            'meta': {}
        }

        self.setPublic(collection, public, save=False)
        if creator:
            self.setUserAccess(
                collection, user=creator, level=AccessType.ADMIN, save=False)

        return self.save(collection)

    def updateCollection(self, collection):
        """
        Updates a collection.

        :param collection: The collection document to update
        :type collection: dict
        :returns: The collection document that was edited.
        """
        collection['updated'] = datetime.datetime.utcnow()

        # Validate and save the collection
        return self.save(collection)

    def load(self, id, level=AccessType.ADMIN, user=None, objectId=True,
             force=False, fields=None, exc=False):
        """
        Calls AccessControlMixin.load, and if no meta field is present,
        adds an empty meta field and saves.

        Takes the same parameters as
        :py:func:`girder.models.model_base.AccessControlMixin.load`.
        """
        doc = super().load(
            id=id, level=level, user=user, objectId=objectId, force=force, fields=fields,
            exc=exc)

        if doc is not None:
            if 'meta' not in doc:
                doc['meta'] = {}
                self.update({'_id': doc['_id']}, {'$set': {
                    'meta': doc['meta']
                }})

        return doc

    def filter(self, doc, user=None, additionalKeys=None):
        """
        Overrides the parent ``filter`` method to add an empty meta field
        (if it doesn't exist) to the returned collection.
        """
        filteredDoc = super().filter(doc, user, additionalKeys=additionalKeys)
        if 'meta' not in filteredDoc:
            filteredDoc['meta'] = {}

        return filteredDoc

    def setMetadata(self, collection, metadata, allowNull=False):
        """
        Set metadata on an collection.  A `ValidationException` is thrown in the
        cases where the metadata JSON object is badly formed, or if any of the
        metadata keys contains a period ('.').

        :param collection: The collection to set the metadata on.
        :type collection: dict
        :param metadata: A dictionary containing key-value pairs to add to
                     the collection's meta field
        :type metadata: dict
        :param allowNull: Whether to allow `null` values to be set in the collection's
                     metadata. If set to `False` or omitted, a `null` value will cause that
                     metadata field to be deleted.
        :returns: the collection document
        """
        if 'meta' not in collection:
            collection['meta'] = {}

        # Add new metadata to existing metadata
        collection['meta'].update(metadata.items())

        # Remove metadata fields that were set to null (use items in py3)
        if not allowNull:
            toDelete = [k for k, v in metadata.items() if v is None]
            for key in toDelete:
                del collection['meta'][key]

        self.validateKeys(collection['meta'])

        collection['updated'] = datetime.datetime.utcnow()

        # Validate and save the collection
        return self.save(collection)

    def deleteMetadata(self, collection, fields):
        """
        Delete metadata on an collection. A `ValidationException` is thrown if the
        metadata field names contain a period ('.') or begin with a dollar sign
        ('$').

        :param collection: The collection to delete metadata from.
        :type collection: dict
        :param fields: An array containing the field names to delete from the
            collection's meta field
        :type field: list
        :returns: the collection document
        """
        self.validateKeys(fields)

        if 'meta' not in collection:
            collection['meta'] = {}

        for field in fields:
            collection['meta'].pop(field, None)

        collection['updated'] = datetime.datetime.utcnow()

        return self.save(collection)

    def fileList(self, doc, user=None, path='', includeMetadata=False,
                 subpath=True, mimeFilter=None, data=True):
        """
        This function generates a list of 2-tuples whose first element is the
        relative path to the file from the collection's root and whose second
        element depends on the value of the `data` flag. If `data=True`, the
        second element will be a generator that will generate the bytes of the
        file data as stored in the assetstore. If `data=False`, the second
        element is the file document itself.

        :param doc: the collection to list.
        :param user: a user used to validate data that is returned.
        :param path: a path prefix to add to the results.
        :param includeMetadata: if True and there is any metadata, include a
                                result which is the JSON string of the
                                metadata.  This is given a name of
                                metadata[-(number).json that is distinct from
                                any file within the item.
        :param subpath: if True, add the collection's name to the path.
        :param mimeFilter: Optional list of MIME types to filter by. Set to
            None to include all files.
        :type mimeFilter: `list or tuple`
        :param data: If True return raw content of each file as stored in the
            assetstore, otherwise return file document.
        :type data: bool
        """
        from .folder import Folder

        if subpath:
            path = os.path.join(path, doc['name'])

        folderModel = Folder()
        # Eagerly evaluate this list, as the MongoDB cursor can time out on long requests
        childFolders = list(folderModel.childFolders(
            parentType='collection', parent=doc, user=user,
            fields=['name'] + (['meta'] if includeMetadata else [])
        ))
        for folder in childFolders:
            for (filepath, file) in folderModel.fileList(
                    folder, user, path, includeMetadata, subpath=True,
                    mimeFilter=mimeFilter, data=data):
                yield (filepath, file)

    def subtreeCount(self, doc, includeItems=True, user=None, level=None):
        """
        Return the size of the folders within the collection.  The collection
        is counted as well.

        :param doc: The collection.
        :param includeItems: Whether items should be included in the count.
        :type includeItems: bool
        :param user: If filtering by permission, the user to filter against.
        :param level: If filtering by permission, the required permission level.
        :type level: AccessLevel
        """
        from .folder import Folder

        count = 1
        folderModel = Folder()
        folders = folderModel.findWithPermissions({
            'parentId': doc['_id'],
            'parentCollection': 'collection'
        }, fields='access', user=user, level=level)

        count += sum(folderModel.subtreeCount(
            folder, includeItems=includeItems, user=user, level=level)
            for folder in folders)
        return count

    def setAccessList(self, doc, access, save=False, recurse=False, user=None,
                      progress=noProgress, setPublic=None, publicFlags=None, force=False):
        """
        Overrides AccessControlledModel.setAccessList to add a recursive
        option. When `recurse=True`, this will set the access list on all
        subfolders to which the given user has ADMIN access level. Any
        subfolders that the given user does not have ADMIN access on will be
        skipped.

        :param doc: The collection to set access settings on.
        :type doc: collection
        :param access: The access control list.
        :type access: dict
        :param save: Whether the changes should be saved to the database.
        :type save: bool
        :param recurse: Whether this access list should be propagated to all
            folders underneath this collection.
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
            from .folder import Folder

            folderModel = Folder()
            folders = folderModel.findWithPermissions({
                'parentId': doc['_id'],
                'parentCollection': 'collection'
            }, user=user, level=AccessType.ADMIN)

            for folder in folders:
                folderModel.setAccessList(
                    folder, access, save=True, recurse=True, user=user,
                    progress=progress, setPublic=setPublic, publicFlags=publicFlags)

        return doc

    def hasCreatePrivilege(self, user):
        """
        Tests whether a given user has the authority to create collections on
        this instance. This is based on the collection creation policy settings.
        By default, only admins are allowed to create collections.

        :param user: The user to test.
        :returns: bool
        """
        from .setting import Setting

        if user['admin']:
            return True

        policy = Setting().get(SettingKey.COLLECTION_CREATE_POLICY)

        if policy['open'] is True:
            return True

        if user['_id'] in policy.get('users', ()):
            return True

        if set(policy.get('groups', ())) & set(user.get('groups', ())):
            return True

        return False

    def countFolders(self, collection, user=None, level=None):
        """
        Returns the number of top level folders under this collection. Access
        checking is optional; to circumvent access checks, pass ``level=None``.

        :param collection: The collection.
        :type collection: dict
        :param user: If performing access checks, the user to check against.
        :type user: dict or None
        :param level: The required access level, or None to return the raw
            top-level folder count.
        """
        from .folder import Folder

        fields = () if level is None else ('access', 'public')

        folderModel = Folder()
        folders = folderModel.findWithPermissions({
            'parentId': collection['_id'],
            'parentCollection': 'collection'
        }, fields=fields, user=user, level=level)

        return folders.count()

    def updateSize(self, doc):
        """
        Recursively recomputes the size of this collection and its underlying
        folders and fixes the sizes as needed.

        :param doc: The collection.
        :type doc: dict
        """
        from .folder import Folder

        size = 0
        fixes = 0
        folderModel = Folder()
        folders = folderModel.find({
            'parentId': doc['_id'],
            'parentCollection': 'collection'
        })
        for folder in folders:
            # fix folder size if needed
            _, f = folderModel.updateSize(folder)
            fixes += f
            # get total recursive folder size
            folder = folderModel.load(folder['_id'], force=True)
            size += folderModel.getSizeRecursive(folder)
        # fix value if incorrect
        if size != doc.get('size'):
            self.update({'_id': doc['_id']}, update={'$set': {'size': size}})
            fixes += 1
        return size, fixes
