#!/usr/bin/env python
# -*- coding: utf-8 -*-

###############################################################################
#  Copyright 2015 Kitware Inc.
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

import itertools
import six

from ..models.model_base import Model, AccessException, GirderException
from ..constants import AccessType


class AccessControlMixin(object):
    """
    This mixin is intended to be used for Model types which aren't access controlled by default,
    but resolve their access controls through another "resource" model object. As such, the
    overridden methods retain the same parameters and only alter functionality related to access
    control resolution.

    The "resource" object can be specified in two different ways:

    First:
      * By setting `resourceColl` on the AccessControlMixin model class, to the "model type
        identifier" of the resource model.
      * By setting `resourceParent` on the AccessControlMixin model class, to the name of a field
        containing the ID of the "resource" object to use for permission checking. This field must
        be set in every object of the AccessControlMixin model collection.
    For example:
    ```
        class Item(AccessControlMixin, Model):
            resourceColl = 'folder'
            resourceParent = 'folderId'
            ...

        class Folder(AccessControlledModel):
            ...

        itemInstance = {
            'folderId': folderInstance['_id'],
            ...
        }
        Item.hasAccess(itemInstance, ...)  # This will check permissions for folderInstance
    ```

    Second (taking precedence over the first):
      * By setting `attachedToType` on an object of the AccessControlMixin model collection, to the
        "model type identifier" of the resource model.
      * By setting `attachedToId` on an object of the AccessControlMixin model collection, to the
        the ID of the "resource" object to use for permission checking.
    For example:
    ```
    class File(AccessControlMixin, Model):
        ...

    class Person(AccessControlledModel):
        ...

    fileInstance = {
        'attachedToType': 'person',
        'attachedToId': personInstance['_id']
        ...
    }
    File.hasAccess(fileInstance, ...)  # This will check permissions for personInstance
    ```

    The "model type identifier" is typically a string with the name of the resource model, exactly
    as passed to `ModelImporter.model`. To reference resource models from plugins, the "model type
    identifier" may also be a list of two strings, for example: ['model_name', 'plugin_name'].
    """
    resourceColl = None
    resourceParent = None

    def _resourceModelandId(self, doc, returnType=False):
        """
        Returns the Model instance and ID of the resource for the given object.

        :param returnType: If True, returns the type identifier for the resource, instead of the
                           resource Model instance.
        """
        if 'attachedToType' in doc and 'attachedToId' in doc:
            # Check 'attachedToType' first, allowing it to override a collection-wide
            # 'resourceParent'.
            resourceType = doc.get('attachedToType')
            resourceId = doc.get('attachedToId')
        else:
            resourceType = self.resourceColl
            resourceId = doc.get(self.resourceParent)

        if returnType:
            return resourceType, resourceId

        if isinstance(resourceType, six.string_types):
            resourceModel = self.model(resourceType)
        elif isinstance(resourceType, list) and len(resourceType) == 2:
            resourceModel = self.model(*resourceType)
        else:
            raise GirderException('Invalid resource parent type.')

        return resourceModel, resourceId

    def load(self, id, level=AccessType.ADMIN, user=None, objectId=True, force=False, fields=None,
             exc=False):
        """
        Calls Model.load for the passed object ID, also ensuring that the resource can be loaded
        with the same credentials.

        Takes the same parameters as
        :py:func:`girder.models.model_base.AccessControlledModel.load`.
        """
        loadFields = fields
        if not force:
            extraFields = {'attachedToId', 'attachedToType'}
            if self.resourceParent:
                extraFields.add(self.resourceParent)
            loadFields = self._supplementFields(fields, extraFields)

        doc = Model.load(self, id=id, objectId=objectId, fields=loadFields, exc=exc)

        if not force and doc is not None:
            resourceModel, resourceId = self._resourceModelandId(doc)
            # Exclude all fields, as no data is actually required from the resource
            # "exc=True" is crucial, so a missing resource doesn't allow access
            resourceModel.load(resourceId, fields=[], level=level, user=user, exc=True)

            self._removeSupplementalFields(doc, fields)

        return doc

    def hasAccess(self, doc, user=None, level=AccessType.READ):
        """
        Determines if a user has access to an object, based on their access to the resource.

        Takes the same parameters as
        :py:func:`girder.models.model_base.AccessControlledModel.hasAccess`.
        """
        resourceModel, resourceId = self._resourceModelandId(doc)

        resource = resourceModel.load(resourceId, force=True)

        return resourceModel.hasAccess(resource, user=user, level=level)

    def hasAccessFlags(self, doc, user=None, flags=None):
        """
        See the documentation of AccessControlledModel.hasAccessFlags, which this wraps.
        """
        if user and user['admin']:
            return True

        if not flags:
            return True

        resourceModel, resourceId = self._resourceModelandId(doc)

        resource = resourceModel.load(resourceId, force=True)

        return resourceModel.hasAccessFlags(resource, user, flags)

    def requireAccess(self, doc, user=None, level=AccessType.READ):
        """
        This wrapper just provides a standard way of throwing an access denied exception if the
        access check fails.
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
            raise AccessException('%s access denied for %s %s (user %s).' %
                                  (perm, self.name, doc.get('_id', 'unknown'), userid))

    def requireAccessFlags(self, doc, user=None, flags=None):
        """
        Provides a standard way of throwing an access exception if a flag access check fails.
        """
        if not self.hasAccessFlags(doc, user, flags):
            if user:
                uid = str(user.get('_id', ''))
            else:
                uid = None

            raise AccessException('Access denied for %s %s (user %s).' %
                                  (self.name, doc.get('_id', 'unknown'), uid))

    def filterResultsByPermission(self, cursor, user, level, limit=0, offset=0,
                                  removeKeys=(), flags=None):
        """
        Yields filtered results from the cursor based on the access control for the resource.

        Takes the same parameters as
        :py:func:`girder.models.model_base.AccessControlledModel.filterResultsByPermission`.
        """
        # Cache mapping (resourceModelName, resourceId) -> access granted (bool)
        resourceAccessCache = {}

        def hasAccess(_result):
            # Calling "_resourceModelandId" with "returnType=True" returns the type of the resource
            # as a hashable string or list, and doesn't call ModelImporter (so it's fast)
            resourceType, resourceId = self._resourceModelandId(_result, returnType=True)

            if isinstance(resourceType, list):
                # lists cannot be used as a dict key
                resourceType = tuple(resourceType)
            cacheKey = (resourceType, resourceId)

            # return cached check if it exists
            if cacheKey in resourceAccessCache:
                return resourceAccessCache[cacheKey]

            # Get the resource's Model instance this time
            resourceModel, resourceId = self._resourceModelandId(_result)
            # Since the resourceId is not cached, check for permissions and set the cache
            resource = resourceModel.load(resourceId, force=True)
            resourceAccess = resourceModel.hasAccess(resource, user=user, level=level)
            if flags:
                resourceAccess = resourceAccess and resourceModel.hasAccessFlags(
                    resource, user=user, flags=flags)

            resourceAccessCache[cacheKey] = resourceAccess
            return resourceAccess

        endIndex = offset + limit if limit else None
        filteredCursor = six.moves.filter(hasAccess, cursor)
        for result in itertools.islice(filteredCursor, offset, endIndex):
            for key in removeKeys:
                if key in result:
                    del result[key]
            yield result

    def textSearch(self, query, user=None, filters=None, limit=0, offset=0,
                   sort=None, fields=None, level=AccessType.READ):
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

        :param user: The user to apply permission filtering for.
        :type user: dict or None
        :param level: The access level to require.
        :type level: girder.constants.AccessType
        """
        filters = filters or {}

        cursor = Model.prefixSearch(
            self, query=query, filters=filters, sort=sort, fields=fields)
        return self.filterResultsByPermission(
            cursor, user=user, level=level, limit=limit, offset=offset)
