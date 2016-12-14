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

from ..models.model_base import Model, AccessException
from ..constants import AccessType


class AccessControlMixin(object):
    """
    This mixin is intended to be used for resources which aren't access
    controlled by default, but resolve their access controls through other
    resources. As such, the overridden methods retain the same parameters and
    only alter functionality related to access control resolution.

    resourceColl corresponds to the resource collection that needs to be used
    for resolution, for example the Item model has a resourceColl of folder.

    resourceParent corresponds to the field in which the parent resource
    belongs, so for an item it would be the folderId.
    """
    resourceColl = None
    resourceParent = None

    def load(self, id, level=AccessType.ADMIN, user=None, objectId=True,
             force=False, fields=None, exc=False):
        """
        Calls Model.load on the current item, and then attempts to load the
        resourceParent which the user must have access to in order to load this
        model.

        Takes the same parameters as
        :py:func:`girder.models.model_base.AccessControlledModel.load`.
        """
        doc = Model.load(self, id=id, objectId=objectId, fields=fields, exc=exc)

        if not force and doc is not None:
            if doc.get(self.resourceParent):
                loadType = self.resourceColl
                loadId = doc[self.resourceParent]
            else:
                loadType = doc.get('attachedToType')
                loadId = doc.get('attachedToId')
            self.model(loadType).load(loadId, level=level, user=user, exc=exc)

        return doc

    def hasAccess(self, resource, user=None, level=AccessType.READ):
        """
        Determines if a user has access to a resource based on their access to
        the resourceParent.

        Takes the same parameters as
        :py:func:`girder.models.model_base.AccessControlledModel.hasAccess`.
        """
        resource = self.model(self.resourceColl) \
                       .load(resource[self.resourceParent], force=True)
        return self.model(self.resourceColl).hasAccess(
            resource, user=user, level=level)

    def hasAccessFlags(self, doc, user=None, flags=None):
        """
        See the documentation of AccessControlledModel.hasAccessFlags, which this wraps.
        """
        if not flags:
            return True

        resource = self.model(self.resourceColl).load(doc[self.resourceParent], force=True)
        return self.model(self.resourceColl).hasAccessFlags(resource, user, flags)

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

    def requireAccessFlags(self, doc, user=None, flags=None):
        """
        See the documentation of AccessControlledModel.requireAccessFlags, which this wraps.
        """
        if not flags:
            return

        resource = self.model(self.resourceColl).load(doc[self.resourceParent], force=True)
        return self.model(self.resourceColl).requireAccessFlags(resource, user, flags)

    def filterResultsByPermission(self, cursor, user, level, limit=0, offset=0,
                                  removeKeys=(), flags=None):
        """
        Yields filtered results from the cursor based on the access control
        existing for the resourceParent.

        Takes the same parameters as
        :py:func:`girder.models.model_base.AccessControlledModel.filterResultsByPermission`.
        """
        # Cache mapping resourceIds -> access granted (bool)
        resourceAccessCache = {}

        def hasAccess(_result):
            resourceId = _result[self.resourceParent]

            # return cached check if it exists
            if resourceId in resourceAccessCache:
                return resourceAccessCache[resourceId]

            # if the resourceId is not cached, check for permission "level"
            # and set the cache
            resource = self.model(self.resourceColl).load(resourceId, force=True)
            val = self.model(self.resourceColl).hasAccess(
                resource, user=user, level=level)

            if flags:
                val = val and self.model(self.resourceColl).hasAccessFlags(
                    resource, user=user, flags=flags)

            resourceAccessCache[resourceId] = val
            return val

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
