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
import pymongo

from bson.objectid import ObjectId
from girder import events
from girder.constants import AccessType, TerminalColor
from girder.utility.model_importer import ModelImporter
from girder.utility import config
from girder.models import getDbConfig, getDbConnection


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

        self.initialize()

        db_cfg = getDbConfig()
        db_connection = getDbConnection()
        cur_config = config.getConfig()
        dbName = db_cfg['database']
        self.database = db_connection[dbName]
        self.collection = self.database[self.name]

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

    def find(self, query={}, offset=0, limit=50, sort=None, fields=None):
        """
        Search the collection by a set of parameters.

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
        return self.collection.find(spec=query, fields=fields, skip=offset,
                                    limit=limit, sort=sort)

    def textSearch(self, query, project):
        """
        Perform a full-text search against the text index for this collection.
        Only call this on models that have declared a text index using
        ensureTextIndex.

        :param query: The text query. Will be stemmed internally.
        :type query: str
        :param project: Project results onto this dictionary.
        :type project: dict
        :returns: The result list. Filtering by permission or any other
                  parameters is left to the caller.
        """
        project['_id'] = 1
        resp = self.database.command("text", self.name, search=query,
                                     project=project)
        return resp['results']

    def save(self, document, validate=True):
        """
        Create or update a document in the collection. This triggers two
        events; one prior to validation, and one prior to saving. Either of
        these events may have their default action prevented.

        :param document: The document to save.
        :type document: dict
        :param validate: Whether to call the model's validate() before saving.
        :type validate: bool
        """
        if validate:
            event = events.trigger('.'.join(('model', self.name, 'validate')),
                                   document)
            if not event.defaultPrevented:
                document = self.validate(document)

        event = events.trigger('.'.join(('model', self.name, 'save')), document)
        if not event.defaultPrevented:
            document['_id'] = self.collection.save(document)

        return document

    def update(self, query, update):
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
        self.collection.update(query, update, multi=True)

    def remove(self, document):
        """
        Delete an object from the collection; must have its _id set.
        """
        assert '_id' in document

        event = events.trigger('.'.join(('model', self.name, 'remove')),
                               document)
        if not event.defaultPrevented:
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
        Fetch a single object from the databse using its _id field. If the
        id is not valid, throws an exception.

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
        if objectId and type(id) is not ObjectId:
            id = ObjectId(id)
        doc = self.collection.find_one({'_id': id}, fields=fields)

        if doc is None and exc is True:
            raise ValidationException('Invalid {} ID: {}'.format(
                                      self.name, id), field='_id')

        return doc

    def filterDocument(self, doc, allow=[]):
        """
        This method will filter the given document to make it suitable to
        output to the user.

        :param doc: The document to filter.
        :type doc: dict
        :param allow: The whitelist of fields to allow in the output document.
        :type allow: List of strings
        """
        if doc is None:
            return None

        out = {}
        for field in allow:
            if field in doc:
                out[field] = doc[field]

        return out


class AccessControlledModel(Model):
    """
    Any model that has access control requirements should inherit from
    this class. It enforces permission checking in the load() method
    and provides convenient methods for testing and requiring user permissions.
    It also provides methods for setting access control policies on the
    resource.
    """

    def _hasGroupAccess(self, perms, groupIds, level):
        """
        Private helper method for checking group access.
        """
        for groupAccess in perms:
            if groupAccess['id'] in groupIds and groupAccess['level'] >= level:
                return True

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
            'users': doc['access'].get('users', []),
            'groups': doc['access'].get('groups', [])
        }

        for user in acList['users']:
            userDoc = self.model('user').load(
                user['id'], force=True,
                fields=['firstName', 'lastName', 'login'])
            user['login'] = userDoc['login']
            user['name'] = '{} {}'.format(
                userDoc['firstName'], userDoc['lastName'])

        for grp in acList['groups']:
            grpDoc = self.model('group').load(
                grp['id'], force=True, fields=['name'])
            grp['name'] = grpDoc['name']

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
            raise AccessException("%s access denied for %s." %
                                  (perm, self.name))

    def load(self, id, level=AccessType.ADMIN, user=None, objectId=True,
             force=False, fields=None, exc=False):
        """
        We override Model.load to also do permission checking.

        :param id: The id of the resource.
        :type id: string or ObjectId
        :param user: The user to check access against.
        :type user: dict or None
        :param level: The required access type for the object.
        :type level: AccessType
        :param force: If you explicity want to circumvent access
                      checking on this resource, set this to True.
        :type force: bool
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

    def filterResultsByPermission(self, cursor, user, level, limit, offset,
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
        :param offset: The offset into the result set.
        :param removeKeys: List of keys that should be removed from each
                           matching document.
        :type removeKeys: list
        """
        count = skipped = 0
        for result in cursor:
            if self.hasAccess(result, user=user, level=level):
                if skipped < offset:
                    skipped += 1
                else:
                    for key in removeKeys:
                        del result[key]
                    yield result
                    count += 1
            if count == limit:
                break

    def filterSearchResults(self, results, user, level=AccessType.READ,
                            limit=20):
        """
        Filter search result list by permissions.
        """
        count = 0
        for result in results:
            if count >= limit:
                break
            obj = result['obj']
            if self.hasAccess(result['obj'], user=user, level=level):
                obj.pop('access', None)
                obj.pop('public', None)
                yield obj
                count += 1

    def textSearch(self, query, project, user=None, limit=20):
        """
        Custom override of Model.textSearch to also force permission-based
        filtering.
        """
        project['access'] = 1
        project['public'] = 1
        results = Model.textSearch(self, query=query, project=project)
        return [r for r in self.filterSearchResults(
            results, user=user, limit=limit)]


class AccessException(Exception):
    """
    Represents denial of access to a resource.
    """
    def __init__(self, message):
        # TODO log the error
        Exception.__init__(self, message)


class ValidationException(Exception):
    """
    Represents validation failure in the model layer. Raise this with
    a message and an optional field property. If one of these is thrown
    in the model during a REST request, it will respond as a 400 status.
    """
    def __init__(self, message, field=None):
        self.field = field

        Exception.__init__(self, message)
