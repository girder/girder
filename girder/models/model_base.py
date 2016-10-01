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

import copy
import functools
import itertools
import pymongo
import re
import six

from bson.objectid import ObjectId
from bson.errors import InvalidId
from pymongo.errors import WriteError
from girder import events, logprint
from girder.constants import AccessType, CoreEventHandler, TEXT_SCORE_SORT_MAX
from girder.external.mongodb_proxy import MongoProxy
from girder.models import getDbConnection
from girder.utility.model_importer import ModelImporter

# pymongo3 complains about extra kwargs to find(), so we must filter them.
_allowedFindArgs = ('cursor_type', 'allow_partial_results', 'oplog_replay',
                    'modifiers', 'manipulate')


class Model(ModelImporter):
    """
    Model base class. Models are responsible for abstracting away the
    persistence layer. Each collection in the database should have its own
    model. Methods that deal with database interaction belong in the
    model layer.
    """

    def __init__(self):
        self.name = None
        self._indices = []
        self._textIndex = None
        self._textLanguage = None
        self.prefixSearchFields = ('lowerName', 'name')

        self._filterKeys = {
            AccessType.READ: set(),
            AccessType.WRITE: set(),
            AccessType.ADMIN: set(),
            AccessType.SITE_ADMIN: set()
        }

        self.initialize()
        self.reconnect()

    def reconnect(self):
        """
        Reconnect to the database and rebuild indices if necessary. Users should
        typically not have to call this method.
        """
        db_connection = getDbConnection()
        self.database = db_connection.get_default_database()
        self.collection = MongoProxy(self.database[self.name])

        for index in self._indices:
            if isinstance(index, (list, tuple)):
                self.collection.create_index(index[0], **index[1])
            else:
                self.collection.create_index(index)

        if isinstance(self._textIndex, dict):
            textIdx = [(k, 'text') for k in six.viewkeys(self._textIndex)]
            try:
                self.collection.create_index(
                    textIdx, weights=self._textIndex,
                    default_language=self._textLanguage)
            except pymongo.errors.OperationFailure:
                logprint.warning('WARNING: Text search not enabled.')

    def exposeFields(self, level, fields):
        """
        Expose model fields to users with the given access level. Subclasses
        should call this in their initialize method to declare what fields
        should be exposed to what access levels if they are using the default
        filter implementation in this class. Since filtered fields are sets,
        this method is idempotent.

        :param level: The required access level for the field.
        :type level: AccessType
        :param fields: A field or list of fields to expose for that level.
        :type fields: str, list, or tuple
        """
        if isinstance(fields, six.string_types):
            fields = (fields, )

        self._filterKeys[level].update(fields)

    def hideFields(self, level, fields):
        """
        Hide a field, i.e. make sure it is not exposed via the default
        filtering method. Since the filter uses a white list, it is only ever
        necessary to call this for fields that were added previously with
        exposeFields().

        :param level: The access level to remove the fields from.
        :type level: AccessType
        :param fields: The field or fields to remove from the white list.
        :type fields: str, list, or tuple
        """
        if isinstance(fields, six.string_types):
            fields = (fields, )

        self._filterKeys[level].difference_update(fields)

    def filter(self, doc, user=None, additionalKeys=None):
        """
        Filter this model for the given user. This is a default implementation
        that assumes this model has no notion of access control, and simply
        allows all keys under READ access level, and conditionally allows any
        keys assigned to SITE_ADMIN level.

        :param doc: The document of this model type to be filtered.
        :type doc: dict or None
        :param user: The current user for whom we are filtering.
        :type user: dict or None
        :param additionalKeys: Any additional keys that should be included in
            the document for this call only.
        :type additionalKeys: list, tuple, set, or None
        :returns: The filtered document (dict).
        """
        if doc is None:
            return None

        keys = set(self._filterKeys[AccessType.READ])

        if user and user['admin']:
            keys.update(self._filterKeys[AccessType.SITE_ADMIN])

        if additionalKeys:
            keys.update(additionalKeys)

        return self.filterDocument(doc, allow=keys)

    def ensureTextIndex(self, index, language='english'):
        """
        Call this during initialize() of the subclass if you want your
        model to have a full-text searchable index. Each collection may
        have zero or one full-text index.

        :param language: The default_language value for the text index,
            which is used for stemming and stop words. If the text index
            should not use stemming and stop words, set this param to 'none'.
        :type language: str
        """
        self._textIndex = index
        self._textLanguage = language

    def ensureIndices(self, indices):
        """
        Subclasses should call this with a list of strings representing
        fields that should be indexed in the database if there are any.
        Otherwise, it is not necessary to call this method. Elements of the list
        may also be a list or tuple, where the second element is a dictionary
        that will be passed as kwargs to the pymongo create_index call.
        """
        self._indices.extend(indices)

    def ensureIndex(self, index):
        """
        Like ensureIndices, but declares just a single index rather than a list
        of them.
        """
        self._indices.append(index)

    def validate(self, doc):
        """
        Models should implement this to validate the document before it enters
        the database. It must return the document with any necessary filters
        applied, or throw a ValidationException if validation of the document
        fails.

        :param doc: The document to validate before saving to the collection.
        :type doc: dict
        """
        raise Exception('Must override validate() in %s model.'
                        % self.__class__.__name__)  # pragma: no cover

    def initialize(self):
        """
        Subclasses should override this and set the name of the collection as
        self.name. Also, they should set any indexed fields that they require.
        """
        raise Exception('Must override initialize() in %s model'
                        % self.__class__.__name__)  # pragma: no cover

    def find(self, query=None, offset=0, limit=0, timeout=None,
             fields=None, sort=None, **kwargs):
        """
        Search the collection by a set of parameters. Passes any extra kwargs
        through to the underlying pymongo.collection.find function.

        :param query: The search query (see general MongoDB docs for "find()")
        :type query: dict
        :param offset: The offset into the results
        :type offset: int
        :param limit: Maximum number of documents to return
        :type limit: int
        :param timeout: Cursor timeout in ms. Default is no timeout.
        :type timeout: int
        :param fields: A mask for filtering result documents by key, or None to return the full
            document, passed to MongoDB find() as the `projection` param.
        :type fields: str, list of strings or tuple of strings for fields to be included from the
            document, or dict for an inclusion or exclusion projection.
        :param sort: The sort order.
        :type sort: List of (key, order) tuples.
        :returns: A pymongo database cursor.
        """
        query = query or {}
        kwargs = {k: kwargs[k] for k in kwargs if k in _allowedFindArgs}

        cursor = self.collection.find(
            filter=query, skip=offset, limit=limit, projection=fields,
            no_cursor_timeout=timeout is None, sort=sort, **kwargs)

        if timeout:
            cursor.max_time_ms(timeout)

        return cursor

    def findOne(self, query=None, fields=None, **kwargs):
        """
        Search the collection by a set of parameters. Passes any kwargs
        through to the underlying pymongo.collection.find_one function.

        :param query: The search query (see general MongoDB docs for "find()")
        :type query: dict
        :param fields: A mask for filtering result documents by key, or None to return the full
            document, passed to MongoDB find() as the `projection` param.
        :type fields: str, list of strings or tuple of strings for fields to be included from the
            document, or dict for an inclusion or exclusion projection.
        :param sort: The sort order.
        :type sort: List of (key, order) tuples.
        :returns: the first object that was found, or None if none found.
        """
        query = query or {}
        kwargs = {k: kwargs[k] for k in kwargs if k in _allowedFindArgs}
        return self.collection.find_one(query, projection=fields, **kwargs)

    def textSearch(self, query, offset=0, limit=0, sort=None, fields=None,
                   filters=None, **kwargs):
        """
        Perform a full-text search against the text index for this collection.

        :param query: The text query. Will be stemmed internally.
        :type query: str
        :param offset: The offset into the results
        :type offset: int
        :param limit: Maximum number of documents to return
        :type limit: int
        :param sort: The sort order.
        :type sort: List of (key, order) tuples.
        :param fields: A mask for filtering result documents by key, or None to return the full
            document, passed to MongoDB find() as the `projection` param.
        :type fields: str, list of strings or tuple of strings for fields to be included from the
            document, or dict for an inclusion or exclusion projection.
        :param filters: Any additional query operators to apply.
        :type filters: dict
        :returns: A pymongo cursor. It is left to the caller to build the
            results from the cursor.
        """
        filters = filters or {}
        fields = fields or {}

        fields['_textScore'] = {'$meta': 'textScore'}
        filters['$text'] = {'$search': query}

        cursor = self.find(filters, offset=offset, limit=limit,
                           sort=sort, fields=fields)

        # Sort by meta text score, but only if result count is below a certain
        # threshold. The text score is not a real index, so we cannot always
        # sort by it if there is a high number of matching documents.
        if cursor.count() < TEXT_SCORE_SORT_MAX and sort is None:
            cursor.sort([('_textScore', {'$meta': 'textScore'})])

        return cursor

    def prefixSearch(self, query, offset=0, limit=0, sort=None, fields=None,
                     filters=None, prefixSearchFields=None, **kwargs):
        """
        Search for documents in this model's collection by a prefix string.
        The fields that will be searched based on this prefix must be set as
        the ``prefixSearchFields`` attribute of this model, which must be an
        iterable. Elements of this iterable must be either a string representing
        the field name, or a 2-tuple in which the first element is the field
        name, and the second element is a string representing the regex search
        options.

        :param query: The prefix string to look for
        :type query: str
        :param offset: The offset into the results
        :type offset: int
        :param limit: Maximum number of documents to return
        :type limit: int
        :param sort: The sort order.
        :type sort: List of (key, order) tuples.
        :param fields: A mask for filtering result documents by key, or None to return the full
            document, passed to MongoDB find() as the `projection` param.
        :type fields: str, list of strings or tuple of strings for fields to be included from the
            document, or dict for an inclusion or exclusion projection.
        :param filters: Any additional query operators to apply.
        :type filters: dict
        :param prefixSearchFields: To override the model's prefixSearchFields
            attribute for this invocation, pass an alternate iterable.
        :returns: A pymongo cursor. It is left to the caller to build the
            results from the cursor.
        """
        filters = filters or {}
        filters['$or'] = filters.get('$or', [])

        for field in (prefixSearchFields or self.prefixSearchFields):
            if isinstance(field, (list, tuple)):
                filters['$or'].append({
                    field[0]: {
                        '$regex': '^%s' % re.escape(query),
                        '$options': field[1]
                    }
                })
            else:
                filters['$or'].append({
                    field: {'$regex': '^%s' % re.escape(query)}
                })

        return self.find(
            filters, offset=offset, limit=limit, sort=sort, fields=fields)

    def save(self, document, validate=True, triggerEvents=True):
        """
        Create or update a document in the collection. This triggers two
        events; one prior to validation, and one prior to saving. Either of
        these events may have their default action prevented.

        :param document: The document to save.
        :type document: dict
        :param validate: Whether to call the model's validate() before saving.
        :type validate: bool
        :param triggerEvents: Whether to trigger events for validate and
            pre- and post-save hooks.
        """
        if validate and triggerEvents:
            event = events.trigger('.'.join(('model', self.name, 'validate')),
                                   document)
            if event.defaultPrevented:
                validate = False

        if validate:
            document = self.validate(document)

        if triggerEvents:
            event = events.trigger('model.%s.save' % self.name, document)
            if event.defaultPrevented:
                return document

        isNew = '_id' not in document
        try:
            if isNew:
                document['_id'] = \
                    self.collection.insert_one(document).inserted_id
            else:
                self.collection.replace_one(
                    {'_id': document['_id']}, document, True)
        except WriteError as e:
            raise ValidationException('Database save failed: %s' % e.details)

        if triggerEvents:
            if isNew:
                events.trigger('model.%s.save.created' % self.name, document)
            events.trigger('model.%s.save.after' % self.name, document)

        return document

    def update(self, query, update, multi=True):
        """
        This method should be used for updating multiple documents in the
        collection. This is useful for things like removing all references in
        this collection to a document that is being deleted from another
        collection.

        For updating a single document, use the save() model method instead.

        :param query: The search query for documents to update,
            see general MongoDB docs for "find()"
        :type query: dict
        :param update: The update specifier.
        :type update: dict
        :param multi: Whether to update a single document, or all matching
            documents.
        :type multi: bool
        :returns: A pymongo UpdateResult object.
        """
        if multi:
            return self.collection.update_many(query, update)
        else:
            return self.collection.update_one(query, update)

    def increment(self, query, field, amount, **kwargs):
        """
        This is a specialization of the update method that atomically increments
        a field by a given amount. Additional kwargs are passed directly through
        to update.

        :param query: The search query for documents to update,
            see general MongoDB docs for "find()"
        :type query: dict
        :param field: The name of the field in the document to increment.
        :type field: str
        :param amount: The amount to increment the field by.
        :type amount: int or float
        """
        self.update(query=query, update={
            '$inc': {field: amount}
        }, **kwargs)

    def remove(self, document, **kwargs):
        """
        Delete an object from the collection; must have its _id set.

        :param document: the item to remove.
        """
        assert '_id' in document

        event = events.trigger('.'.join(('model', self.name, 'remove')),
                               document)
        kwargsEvent = events.trigger(
            '.'.join(('model', self.name, 'remove_with_kwargs')), {
                'document': document,
                'kwargs': kwargs
            })

        if not event.defaultPrevented and not kwargsEvent.defaultPrevented:
            return self.collection.delete_one({'_id': document['_id']})

    def removeWithQuery(self, query):
        """
        Remove all documents matching a given query from the collection.
        For safety reasons, you may not pass an empty query.

        :param query: The search query for documents to delete,
            see general MongoDB docs for "find()"
        :type query: dict
        """
        assert query

        return self.collection.delete_many(query)

    def load(self, id, objectId=True, fields=None, exc=False):
        """
        Fetch a single object from the database using its _id field.

        :param id: The value for searching the _id field.
        :type id: string or ObjectId
        :param objectId: Whether the id should be coerced to ObjectId type.
        :type objectId: bool
        :param fields: A mask for filtering result documents by key, or None to return the full
            document, passed to MongoDB find() as the `projection` param.
        :type fields: str, list of strings or tuple of strings for fields to be included from the
            document, or dict for an inclusion or exclusion projection.
        :param exc: Whether to raise a ValidationException if there is no
                    document with the given id.
        :type exc: bool
        :returns: The matching document, or None.
        """
        if not id:
            raise ValidationException('Attempt to load null ObjectId: %s' % id)

        if objectId and not isinstance(id, ObjectId):
            try:
                id = ObjectId(id)
            except InvalidId:
                raise ValidationException('Invalid ObjectId: %s' % id,
                                          field='id')
        doc = self.findOne({'_id': id}, fields=fields)

        if doc is None and exc is True:
            raise ValidationException('No such %s: %s' % (self.name, id),
                                      field='id')

        return doc

    def filterDocument(self, doc, allow=None):
        """
        This method will filter the given document to make it suitable to
        output to the user.

        :param doc: The document to filter.
        :type doc: dict
        :param allow: The whitelist of fields to allow in the output document.
        :type allow: List of strings
        """
        if not allow:
            allow = []

        if doc is None:
            return None

        out = {}
        for field in allow:
            if field in doc:
                out[field] = doc[field]

        if '_textScore' in doc:
            out['_textScore'] = doc['_textScore']

        out['_modelType'] = self.name

        return out

    def subtreeCount(self, doc):
        """
        Return the size of the subtree rooted at the given document.  In
        general, if this contains items or folders, it will be the count of the
        items and folders in all containers.  If it does not, it will be 1.
        This returns the absolute size of the subtree, it does not filter by
        permissions.

        :param doc: The root of the subtree.
        :type doc: dict
        """
        return 1

    def _isInclusionProjection(self, fields):
        """
        Test whether a projection filter is an inclusion filter (whitelist) or exclusion
        projection (blacklist) of fields, as defined by MongoDB find() method `projection` param.

        :param fields: A mask for filtering result documents by key, or None to return the full
            document, passed to MongoDB find() as the `projection` param.
        :type fields: str, list of strings or tuple of strings for fields to be included from the
            document, or dict for an inclusion or exclusion projection.
        """
        if fields is None:
            return False

        if not isinstance(fields, dict):
            # If this is a list/tuple/set, that means inclusion
            return True

        for k, v in six.viewitems(fields):
            if k != '_id':
                # We are only allowed either inclusion or exclusion keys in a dict, there can be no
                # mixing of these, with the only exception being that the `_id` key can be set as
                # an exclusion field in a dict that otherwise holds inclusion fields.
                return v

        # Empty dict or just _id field
        return fields.get('_id', True)


class AccessControlledModel(Model):
    """
    Any model that has access control requirements should inherit from
    this class. It enforces permission checking in the load() method
    and provides convenient methods for testing and requiring user permissions.
    It also provides methods for setting access control policies on the
    resource.
    """

    def __init__(self):
        # Do the bindings before calling __init__(), in case a derived class
        # wants to change things in initialize()
        events.bind('model.user.remove',
                    CoreEventHandler.ACCESS_CONTROL_CLEANUP,
                    self._cleanupDeletedEntity)
        events.bind('model.group.remove',
                    CoreEventHandler.ACCESS_CONTROL_CLEANUP,
                    self._cleanupDeletedEntity)
        super(AccessControlledModel, self).__init__()

    def _cleanupDeletedEntity(self, event):
        """
        This callback removes references to deleted users or groups from all
        concrete AccessControlledModel subtypes.

        This generally should not be called or overridden directly. This should
        not be unregistered, that would allow references to non-existent users
        and groups to remain.
        """
        entityType = event.name.split('.')[1]
        entityDoc = event.info

        if entityType == self.name:
            # Avoid circular callbacks, since Users and Groups are themselves
            # AccessControlledModels
            return

        if entityType == 'user':
            # Remove creator references for this user entity.
            creatorQuery = {
                'creatorId': entityDoc['_id']
            }
            creatorUpdate = {
                '$set': {'creatorId': None}
            }
            # If a given access-controlled resource doesn't store creatorId,
            # this will simply do nothing
            self.update(creatorQuery, creatorUpdate)

        # Remove references to this entity from access-controlled resources.
        acQuery = {
            'access.%ss.id' % entityType: entityDoc['_id']
        }
        acUpdate = {
            '$pull': {
                'access.%ss' % entityType: {'id': entityDoc['_id']}
            }
        }
        self.update(acQuery, acUpdate)

    def filter(self, doc, user, additionalKeys=None):
        """
        Filter this model for the given user according to the user's access
        level. Also adds the special _accessLevel field to the document to
        indicate the user's highest access level. This filters a single document
        that the user has at least read access to. For filtering a set of
        documents, see filterResultsByPermission().

        :param doc: The document of this model type to be filtered.
        :type doc: dict or None
        :param user: The current user for whom we are filtering.
        :type user: dict or None
        :param additionalKeys: Any additional keys that should be included in
            the document for this call only.
        :type additionalKeys: list, tuple, or None
        :returns: The filtered document (dict).
        """
        if doc is None:
            return None

        keys = set(self._filterKeys[AccessType.READ])
        level = self.getAccessLevel(doc, user)

        if level >= AccessType.WRITE:
            keys.update(self._filterKeys[AccessType.WRITE])

            if level >= AccessType.ADMIN:
                keys.update(self._filterKeys[AccessType.ADMIN])

                if user['admin']:
                    keys.update(self._filterKeys[AccessType.SITE_ADMIN])

        if additionalKeys:
            keys.update(additionalKeys)

        filtered = self.filterDocument(doc, allow=keys)
        filtered['_accessLevel'] = level

        return filtered

    def _hasGroupAccess(self, perms, groupIds, level):
        """
        Private helper method for checking group access.
        """
        for groupAccess in perms:
            if groupAccess['id'] in groupIds and groupAccess['level'] >= level:
                return True
        return False

    def _hasUserAccess(self, perms, userId, level):
        """
        Private helper method for checking user-specific access.
        """
        for userAccess in perms:
            if userAccess['id'] == userId and userAccess['level'] >= level:
                return True
        return False

    def _setAccess(self, doc, id, entity, level, save):
        """
        Private helper for setting access on a resource.
        """
        assert entity == 'users' or entity == 'groups'
        if not isinstance(id, ObjectId):
            id = ObjectId(id)

        if 'access' not in doc:
            doc['access'] = {'groups': [], 'users': []}
        if entity not in doc['access']:
            doc['access'][entity] = []

        # First remove any existing permission level for this entity.
        doc['access'][entity] = [perm for perm in doc['access'][entity]
                                 if perm['id'] != id]

        # Add in the new level for this entity unless we are removing access.
        if level is not None:
            doc['access'][entity].append({
                'id': id,
                'level': level
            })

        if save:
            doc = self.save(doc)

        return doc

    def setPublic(self, doc, public, save=False):
        """
        Set the flag for public read access on the object.

        :param doc: The document to update permissions on.
        :type doc: dict
        :param public: Flag for public read access.
        :type public: bool
        :param save: Whether to save the object to the database afterward.
                     Set this to False if you want to wait to save the
                     document for performance reasons.
        :type save: bool
        :returns: The updated resource document.
        """
        assert isinstance(public, bool)

        doc['public'] = public

        if save:
            doc = self.save(doc)

        return doc

    def setAccessList(self, doc, access, save=False):
        """
        Set the entire access control list to the given value. This also saves
        the resource in its new state to the database.

        :param doc: The resource to update.
        :type doc: dict
        :param access: The new access control list to set on the object.
        :type access: dict
        :param save: Whether to save after updating.
        :type save: boolean
        :returns: The updated resource.
        """

        # First coerce the access list value into a valid form.
        acList = {
            'users': [],
            'groups': []
        }

        for userAccess in access.get('users', []):
            if 'id' in userAccess and 'level' in userAccess:
                if not userAccess['level'] in (AccessType.READ,
                                               AccessType.WRITE,
                                               AccessType.ADMIN):
                    raise ValidationException('Invalid access level', 'access')

                acList['users'].append({
                    'id': ObjectId(userAccess['id']),
                    'level': userAccess['level']
                })
            else:
                raise ValidationException('Invalid access list', 'access')

        for groupAccess in access.get('groups', []):
            if 'id' in groupAccess and 'level' in groupAccess:
                if not groupAccess['level'] in (AccessType.READ,
                                                AccessType.WRITE,
                                                AccessType.ADMIN):
                    raise ValidationException('Invalid access level', 'access')

                acList['groups'].append({
                    'id': ObjectId(groupAccess['id']),
                    'level': groupAccess['level']
                })
            else:
                raise ValidationException('Invalid access list', 'access')

        doc['access'] = acList

        if save:
            doc = self.save(doc)

        return doc

    def setGroupAccess(self, doc, group, level, save=False):
        """
        Set group-level access on the resource.

        :param doc: The resource document to set access on.
        :type doc: dict
        :param group: The group to grant or remove access to.
        :type group: dict
        :param level: What level of access the group should have. Set to None
                      to remove all access for this group.
        :type level: AccessType or None
        :param save: Whether to save the object to the database afterward.
                     Set this to False if you want to wait to save the
                     document for performance reasons.
        :type save: bool
        :returns: The updated resource document.
        """
        return self._setAccess(doc, group['_id'], 'groups', level, save)

    def getAccessLevel(self, doc, user):
        """
        Return the maximum access level for a given user on a given object.
        This can be useful for alerting the user which set of actions they are
        able to perform on the object in advance of trying to call them.

        :param doc: The object to check access on.
        :param user: The user to get the access level for.
        :returns: The max AccessType available for the user on the object.
        """
        if user is None:
            if doc.get('public', False):
                return AccessType.READ
            else:
                return AccessType.NONE
        elif user['admin']:
            return AccessType.ADMIN
        else:
            access = doc.get('access', {})
            level = AccessType.NONE

            for group in access.get('groups', []):
                if group['id'] in user.get('groups', []):
                    level = max(level, group['level'])
                    if level == AccessType.ADMIN:
                        return level

            for userAccess in access.get('users', []):
                if userAccess['id'] == user['_id']:
                    level = max(level, userAccess['level'])
                    if level == AccessType.ADMIN:
                        return level

            return level

    def getFullAccessList(self, doc):
        """
        Return an object representing the full access list on this document.
        This simply includes the names of the users and groups with the ACL.

        If the document contains references to users or groups that no longer
        exist, they are simply removed from the ACL, and the modified ACL is
        persisted at the end of this method if any removals occurred.

        :param doc: The document whose ACL to return.
        :type doc: dict
        :returns: A dict containing `users` and `groups` keys.
        """
        acList = {
            'users': doc.get('access', {}).get('users', []),
            'groups': doc.get('access', {}).get('groups', [])
        }

        dirty = False

        for user in acList['users'][:]:
            userDoc = self.model('user').load(
                user['id'], force=True,
                fields=['firstName', 'lastName', 'login'])
            if not userDoc:
                dirty = True
                acList['users'].remove(user)
                continue
            user['login'] = userDoc['login']
            user['name'] = ' '.join((userDoc['firstName'], userDoc['lastName']))

        for grp in acList['groups'][:]:
            grpDoc = self.model('group').load(
                grp['id'], force=True, fields=['name', 'description'])
            if not grpDoc:
                dirty = True
                acList['groups'].remove(grp)
                continue
            grp['name'] = grpDoc['name']
            grp['description'] = grpDoc['description']

        if dirty:
            # If we removed invalid entries from the ACL, persist the changes.
            self.setAccessList(doc, acList, save=True)

        return acList

    def setUserAccess(self, doc, user, level, save=False):
        """
        Set user-level access on the resource.

        :param doc: The resource document to set access on.
        :type doc: dict
        :param user: The user to grant or remove access to.
        :type user: dict
        :param level: What level of access the user should have. Set to None
                      to remove all access for this user.
        :type level: AccessType or None
        :param save: Whether to save the object to the database afterward.
                     Set this to False if you want to wait to save the
                     document for performance reasons.
        :type save: bool
        :returns: The modified resource document.
        """
        return self._setAccess(doc, user['_id'], 'users', level, save)

    def hasAccess(self, doc, user=None, level=AccessType.READ):
        """
        This method looks through the object's permission set and determines
        whether the user has the given permission level on the object.

        :param doc: The document to check permission on.
        :type doc: dict
        :param user: The user to check against.
        :type user: dict
        :param level: The access level.
        :type level: AccessType
        :returns: Whether the access is granted.
        """
        if level <= AccessType.READ and doc.get('public', False) is True:
            # Short-circuit the case of public resources
            return True
        elif user is None:
            # Anonymous users can only see public resources
            return False

        if user['admin']:
            # Short-circuit the case of admins
            return True

        # If all that fails, descend into real permission checking.
        if 'access' in doc:
            perms = doc['access']
            if self._hasGroupAccess(perms.get('groups', []),
                                    user.get('groups', []), level):
                return True
            elif self._hasUserAccess(perms.get('users', []),
                                     user['_id'], level):
                return True

        return False

    def requireAccess(self, doc, user=None, level=AccessType.READ):
        """
        This wrapper just provides a standard way of throwing an
        access denied exception if the access check fails.
        """
        if not self.hasAccess(doc, user, level):
            if level == AccessType.READ:
                perm = 'Read'
            elif level == AccessType.WRITE:
                perm = 'Write'
            elif level in (AccessType.ADMIN, AccessType.SITE_ADMIN):
                perm = 'Admin'
            else:
                perm = 'Unknown level'
            if user:
                userid = str(user.get('_id', ''))
            else:
                userid = None
            raise AccessException("%s access denied for %s %s (user %s)." %
                                  (perm, self.name, doc.get('_id', 'unknown'),
                                   userid))

    def load(self, id, level=AccessType.ADMIN, user=None, objectId=True,
             force=False, fields=None, exc=False):
        """
        Override of Model.load to also do permission checking.

        :param id: The id of the resource.
        :type id: str or ObjectId
        :param level: The required access type for the object.
        :type level: AccessType
        :param user: The user to check access against.
        :type user: dict or None
        :param objectId: Whether the id should be coerced to ObjectId type.
        :type objectId: bool
        :param force: If you explicitly want to circumvent access
                      checking on this resource, set this to True.
        :type force: bool
        :param fields: A mask for filtering result documents by key, or None to return the full
            document, passed to MongoDB find() as the `projection` param.
        :type fields: str, list of strings or tuple of strings for fields to be included from the
            document, or dict for an inclusion or exclusion projection.
        :param exc: If not found, throw a ValidationException instead of
            returning None.
        :type exc: bool
        :raises ValidationException: If an invalid ObjectId is passed.
        :returns: The matching document, or None if no match exists.
        """

        # Ensure we include access and public, they are needed by requireAccess
        loadFields = copy.copy(fields)
        if not force and self._isInclusionProjection(fields):
            if isinstance(loadFields, dict):
                loadFields['access'] = True
                loadFields['public'] = True
            else:
                loadFields = list(set(loadFields) | {'access', 'public'})

        doc = Model.load(self, id=id, objectId=objectId, fields=loadFields,
                         exc=exc)

        if not force and doc is not None:
            self.requireAccess(doc, user, level)

            if fields is not None:
                if 'access' not in fields:
                    del doc['access']

                if 'public' not in fields:
                    del doc['public']

        return doc

    def list(self, user=None, limit=0, offset=0, sort=None):
        """
        Return a list of documents that are visible to a user.

        :param user: The user to filter for
        :type user: dict or None
        :param limit: Maximum number of documents to return
        :type limit: int
        :param offset: The offset into the results
        :type offset: int
        :param sort: The sort order
        :type sort: List of (key, order) tuples
        """
        cursor = self.find({}, sort=sort)
        return self.filterResultsByPermission(
            cursor=cursor, user=user, level=AccessType.READ, limit=limit,
            offset=offset)

    def copyAccessPolicies(self, src, dest, save=False):
        """
        Copies the set of access control policies from one document to another.

        :param src: The source document to copy policies from.
        :type src: dict
        :param dest: The destination document to copy policies onto.
        :type dest: dict
        :param save: Whether to save the destination document after copying.
        :type save: bool
        :returns: The modified destination document.
        """
        dest['public'] = src.get('public', False)
        if 'access' in src:
            dest['access'] = copy.deepcopy(src['access'])

        if save:
            dest = self.save(dest)
        return dest

    def filterResultsByPermission(self, cursor, user, level, limit=0, offset=0,
                                  removeKeys=()):
        """
        Given a database result cursor, this generator will yield only the
        results that the user has the given level of access on, respecting the
        limit and offset specified.

        :param cursor: The database cursor object from "find()".
        :param user: The user to check policies against.
        :type user: dict or None
        :param level: The access level.
        :type level: AccessType
        :param limit: Maximum number of documents to return
        :type limit: int
        :param offset: The offset into the results
        :type offset: int
        :param removeKeys: List of keys that should be removed from each
                           matching document.
        :type removeKeys: list
        """
        hasAccess = functools.partial(self.hasAccess, user=user, level=level)

        endIndex = offset + limit if limit else None
        filteredCursor = six.moves.filter(hasAccess, cursor)
        for result in itertools.islice(filteredCursor, offset, endIndex):
            for key in removeKeys:
                if key in result:
                    del result[key]
            yield result

    def textSearch(self, query, user=None, filters=None, limit=0, offset=0,
                   sort=None, fields=None, level=AccessType.READ):
        """
        Custom override of Model.textSearch to also force permission-based
        filtering. The parameters are the same as Model.textSearch.

        :param query: The text query. Will be stemmed internally.
        :type query: str
        :param user: The user to apply permission filtering for.
        :type user: dict or None
        :param filters: Any additional query operators to apply.
        :type filters: dict
        :param limit: Maximum number of documents to return
        :type limit: int
        :param offset: The offset into the results
        :type offset: int
        :param sort: The sort order
        :type sort: List of (key, order) tuples
        :param fields: A mask for filtering result documents by key, or None to return the full
            document, passed to MongoDB find() as the `projection` param.
        :type fields: str, list of strings or tuple of strings for fields to be included from the
            document, or dict for an inclusion or exclusion projection.
        :param level: The access level to require.
        :type level: girder.constants.AccessType
        """
        filters = filters or {}

        cursor = Model.textSearch(
            self, query=query, filters=filters, sort=sort, fields=fields)
        return self.filterResultsByPermission(
            cursor, user=user, level=level, limit=limit, offset=offset)

    def prefixSearch(self, query, user=None, filters=None, limit=0, offset=0,
                     sort=None, fields=None, level=AccessType.READ):
        """
        Custom override of Model.prefixSearch to also force permission-based
        filtering. The parameters are the same as Model.prefixSearch.

        :param query: The prefix string to look for
        :type query: str
        :param user: The user to apply permission filtering for.
        :type user: dict or None
        :param filters: Any additional query operators to apply.
        :type filters: dict
        :param limit: Maximum number of documents to return
        :type limit: int
        :param offset: The offset into the results
        :type offset: int
        :param sort: The sort order.
        :type sort: List of (key, order) tuples.
        :param fields: A mask for filtering result documents by key, or None to return the full
            document, passed to MongoDB find() as the `projection` param.
        :type fields: str, list of strings or tuple of strings for fields to be included from the
            document, or dict for an inclusion or exclusion projection.
        :param level: The access level to require.
        :type level: girder.constants.AccessType
        :returns: A pymongo cursor. It is left to the caller to build the
            results from the cursor.
        """
        filters = filters or {}

        cursor = Model.prefixSearch(
            self, query=query, filters=filters, sort=sort, fields=fields)
        return self.filterResultsByPermission(
            cursor, user=user, level=level, limit=limit, offset=offset)


class AccessException(Exception):
    """
    Represents denial of access to a resource.
    """
    def __init__(self, message, extra=None):
        self.message = message
        self.extra = extra

        Exception.__init__(self, message)


class GirderException(Exception):
    """
    Represents a general exception that might occur in regular use.  From the
    user perspective, these are failures, but not catastrophic ones.  An
    identifier can be passed, which allows receivers to check the exception
    without relying on the text of the message.  It is recommended that
    identifiers are a dot-separated string consisting of the originating
    python module and a distinct error.  For example,
    'girder.model.assetstore.no-current-assetstore'.
    """
    def __init__(self, message, identifier=None):
        self.identifier = identifier
        self.message = message

        Exception.__init__(self, message)


class ValidationException(Exception):
    """
    Represents validation failure in the model layer. Raise this with
    a message and an optional field property. If one of these is thrown
    in the model during a REST request, it will respond as a 400 status.
    """
    def __init__(self, message, field=None):
        self.field = field
        self.message = message

        Exception.__init__(self, message)
