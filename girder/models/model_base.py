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

import functools
import itertools
import pymongo
import six

from girder.external.mongodb_proxy import MongoProxy

from bson.objectid import ObjectId
from girder import events
from girder.constants import AccessType, TerminalColor, TEXT_SCORE_SORT_MAX
from girder.utility.model_importer import ModelImporter
from girder.models import getDbConnection


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

        self._filterKeys = {
            AccessType.READ: set('_id'),
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
                self.collection.ensure_index(index[0], **index[1])
            else:
                self.collection.ensure_index(index)

        if type(self._textIndex) is dict:
            textIdx = [(k, 'text') for k in self._textIndex.keys()]
            try:
                self.collection.ensure_index(
                    textIdx, weights=self._textIndex,
                    default_language=self._textLanguage)
            except pymongo.errors.OperationFailure:
                print(
                    TerminalColor.warning('WARNING: Text search not enabled.'))

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

        self._filterKeys[level] = self._filterKeys[level].union(fields)

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

        self._filterKeys[level] = self._filterKeys[level].difference(fields)

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
        :type additionalKeys: list, tuple, or None
        :returns: The filtered document (dict).
        """
        if doc is None:
            return None

        keys = self._filterKeys[AccessType.READ]

        if user and user.get('admin') is True:
            keys = keys.union(self._filterKeys[AccessType.SITE_ADMIN])

        if additionalKeys:
            keys = keys.union(additionalKeys)

        return self.filterDocument(doc, allow=tuple(keys))

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
        that will be passed as kwargs to the pymongo ensure_index call.
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

    def find(self, query=None, offset=0, limit=0, **kwargs):
        """
        Search the collection by a set of parameters. Passes any kwargs
        through to the underlying pymongo.collection.find function.

        :param query: The search query (see general MongoDB docs for "find()")
        :type query: dict
        :param offset: The offset into the results
        :type offset: int
        :param limit: Maximum number of documents to return
        :type limit: int
        :param sort: The sort order.
        :type sort: List of (key, order) tuples.
        :param fields: A mask for filtering result documents by key.
        :type fields: List of strings
        :returns: A pymongo database cursor.
        """
        if not query:
            query = {}

        if 'timeout' not in kwargs:
            kwargs['timeout'] = False

        return self.collection.find(
            spec=query, skip=offset, limit=limit, **kwargs)

    def findOne(self, query=None, **kwargs):
        """
        Search the collection by a set of parameters. Passes any kwargs
        through to the underlying pymongo.collection.find function.

        :param query: The search query (see general MongoDB docs for "find()")
        :type query: dict
        :param sort: The sort order.
        :type sort: List of (key, order) tuples.
        :param fields: A mask for filtering result documents by key.
        :type fields: List of strings
        :returns: the first object that was found, or None if none found.
        """
        if not query:
            query = {}
        return self.collection.find_one(query, **kwargs)

    def textSearch(self, query, offset=0, limit=0, sort=None, fields=None,
                   filters=None):
        """
        Perform a full-text search against the text index for this collection.

        :param query: The text query. Will be stemmed internally.
        :type query: str
        :param filters: Any additional query operators to apply.
        :type filters: dict
        :returns: A pymongo cursor. It is left to the caller to build the
            results from the cursor.
        """
        if not filters:
            filters = {}
        if not fields:
            fields = {}

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
            event = events.trigger('model.{}.save'.format(self.name), document)
            if event.defaultPrevented:
                return document

        sendCreateEvent = ('_id' not in document)
        document['_id'] = self.collection.save(document)

        if triggerEvents:
            if sendCreateEvent:
                events.trigger('model.{}.save.created'.format(self.name),
                               document)
            events.trigger('model.{}.save.after'.format(self.name), document)

        return document

    def update(self, query, update, multi=True):
        """
        This method should be used for updating multiple documents in the
        collection. This is useful for things like removing all references in
        this collection to a document that is being deleted from another
        collection.

        This is a thin wrapper around pymongo db.collection.update().

        For updating a single document, use the save() model method instead.

        :param query: The query for finding documents to update. It's
                      the same format as would be passed to find().
        :type query: dict
        :param update: The update specifier.
        :type update: dict
        """
        self.collection.update(query, update, multi=multi)

    def increment(self, query, field, amount, **kwargs):
        """
        This is a specialization of the update method that atomically increments
        a field by a given amount. Additional kwargs are passed directly through
        to update.

        :param query: The query selector for documents to update.
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

        :param doc: the item to remove.
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
            return self.collection.remove({'_id': document['_id']})

    def removeWithQuery(self, query):
        """
        Remove all documents matching a given query from the collection.
        For safety reasons, you may not pass an empty query.
        """
        assert query

        return self.collection.remove(query)

    def load(self, id, objectId=True, fields=None, exc=False):
        """
        Fetch a single object from the database using its _id field.

        :param id: The value for searching the _id field.
        :type id: string or ObjectId
        :param objectId: Whether the id should be coerced to ObjectId type.
        :type objectId: bool
        :param fields: Fields list to include. Also can be a dict for
                       exclusion. See pymongo docs for how to use this arg.
        :param exc: Whether to raise a ValidationException if there is no
                    document with the given id.
        :type exc: bool
        :returns: The matching document, or None.
        """
        if not id:
            raise Exception('Attempt to load null ObjectId: %s' % id)

        if objectId and type(id) is not ObjectId:
            try:
                id = ObjectId(id)
            except Exception:
                raise ValidationException('Invalid ObjectId: {}'.format(id),
                                          field='id')
        doc = self.collection.find_one({'_id': id}, fields=fields)

        if doc is None and exc is True:
            raise ValidationException('No such {}: {}'.format(
                                      self.name, id), field='id')

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


class AccessControlledModel(Model):
    """
    Any model that has access control requirements should inherit from
    this class. It enforces permission checking in the load() method
    and provides convenient methods for testing and requiring user permissions.
    It also provides methods for setting access control policies on the
    resource.
    """

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

        keys = self._filterKeys[AccessType.READ]
        level = self.getAccessLevel(doc, user)

        if level >= AccessType.WRITE:
            keys = keys.union(self._filterKeys[AccessType.WRITE])

            if level >= AccessType.ADMIN:
                keys = keys.union(self._filterKeys[AccessType.ADMIN])

                if user.get('admin') is True:
                    keys = keys.union(
                        self._filterKeys[AccessType.SITE_ADMIN])

        if additionalKeys:
            keys = keys.union(additionalKeys)

        filtered = self.filterDocument(doc, allow=tuple(keys))
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
        if type(id) is not ObjectId:
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
            doc = self.save(doc, validate=False)

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
        assert type(public) is bool

        doc['public'] = public

        if save:
            doc = self.save(doc, validate=False)

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
            doc = self.save(doc, validate=False)

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
        elif user.get('admin', False):
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
        This simply includes the names of the users and groups with the access
        list.
        """
        acList = {
            'users': doc.get('access', {}).get('users', []),
            'groups': doc.get('access', {}).get('groups', [])
        }

        for user in acList['users']:
            userDoc = self.model('user').load(
                user['id'], force=True,
                fields=['firstName', 'lastName', 'login'])
            user['login'] = userDoc['login']
            user['name'] = ' '.join((userDoc['firstName'], userDoc['lastName']))

        for grp in acList['groups']:
            grpDoc = self.model('group').load(
                grp['id'], force=True, fields=['name', 'description'])
            grp['name'] = grpDoc['name']
            grp['description'] = grpDoc['description']

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
        if user is None:
            # Short-circuit the case of anonymous users
            return level == AccessType.READ and doc.get('public', False) is True
        elif user.get('admin', False) is True:
            # Short-circuit the case of admins
            return True
        else:
            # Short-circuit the case of public resources
            if level == AccessType.READ and doc.get('public', False) is True:
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
            else:
                perm = 'Admin'
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
        :param user: The user to check access against.
        :type user: dict or None
        :param level: The required access type for the object.
        :type level: AccessType
        :param force: If you explicitly want to circumvent access
                      checking on this resource, set this to True.
        :type force: bool
        :param objectId: Whether the _id field is an ObjectId.
        :type objectId: bool
        :param fields: The subset of fields to load from the returned document,
            or None to return the full document.
        :param exc: If not found, throw a ValidationException instead of
            returning None.
        :type exc: bool
        :raises ValidationException: If an invalid ObjectId is passed.
        :returns: The matching document, or None if no match exists.
        """
        doc = Model.load(self, id=id, objectId=objectId, fields=fields, exc=exc)

        if not force and doc is not None:
            self.requireAccess(doc, user, level)

        return doc

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
            dest['access'] = src['access']

        if save:
            dest = self.save(dest, validate=False)
        return dest

    def filterResultsByPermission(self, cursor, user, level, limit, offset=0,
                                  removeKeys=()):
        """
        Given a database result cursor, this generator will yield only the
        results that the user has the given level of access on, respecting the
        limit and offset specified.

        :param cursor: The database cursor object from "find()".
        :param user: The user to check policies against.
        :param level: The access level.
        :type level: AccessType
        :param limit: The max size of the result set.
        :type limit: int
        :param offset: The offset into the result set.
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
                   sort=None, fields=None):
        """
        Custom override of Model.textSearch to also force permission-based
        filtering. The parameters are the same as Model.textSearch.

        :param user: The user to apply permission filtering for.
        """
        if not filters:
            filters = {}

        cursor = Model.textSearch(
            self, query=query, filters=filters, sort=sort, fields=fields)
        return self.filterResultsByPermission(
            cursor, user=user, level=AccessType.READ, limit=limit,
            offset=offset)


class AccessException(Exception):
    """
    Represents denial of access to a resource.
    """
    def __init__(self, message):
        self.message = message

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
