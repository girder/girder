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

from ..models.model_base import Model
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

        if doc is not None:
            if self.resourceParent in doc and doc[self.resourceParent]:
                loadType = self.resourceColl
                loadId = doc[self.resourceParent]
            else:
                loadType = doc['attachedToType']
                loadId = doc['attachedToId']

        if not force and doc is not None:
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
        return self.model(self.resourceColl).hasAccess(resource, user=user,
                                                       level=level)

    def filterResultsByPermission(self, cursor, user, level, limit, offset,
                                  removeKeys=()):
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
            resource = self.model(self.resourceColl).load(resourceId,
                                                          force=True)
            resourceAccessCache[resourceId] = \
                self.model(self.resourceColl).hasAccess(
                    resource, user=user, level=level)

            return resourceAccessCache[resourceId]

        endIndex = offset + limit if limit else None
        filteredCursor = six.moves.filter(hasAccess, cursor)
        for result in itertools.islice(filteredCursor, offset, endIndex):
            for key in removeKeys:
                if key in result:
                    del result[key]
            yield result
