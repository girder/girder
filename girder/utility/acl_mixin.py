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
    resources.

    resource_coll corresponds to the resource collection that needs to be used
    for resolution, for example an item would resolve its resource_coll as
    folder (if it weren't already access controlled).

    resource_parent corresponds to the field in which the parent resource
    belongs, so for an item it would be the folderId.
    """
    resource_coll = None
    resource_parent = None

    def load(self, id, level=AccessType.ADMIN, user=None, objectId=True,
             force=False, fields=None, exc=False):
        doc = Model.load(self, id=id, objectId=objectId, fields=fields, exc=exc)

        if not force and doc is not None:
            """ this is done to load the resource for side effects only,
            primarily we just want it to raise an exception if the user doesn't
            have permission to view it. """
            self.model(self.resource_coll).load(doc[self.resource_parent], level, user, objectId,
                                              force, fields, exc)

        return doc

    def hasAccess(self, file, user=None, level=AccessType.READ):
        resource = self.model(self.resource_coll).load(file[self.resource_parent], force=True)
        return self.model(self.resource_coll).hasAccess(resource, user=user, level=level)

    def filterResultsByPermission(self, cursor, user, level, limit, offset,
                                  removeKeys=()):
        # Cache mapping resourceIds -> access granted (bool)
        resourceAccessCache = {}

        def hasAccess(_result):
            resourceId = _result[self.resource_parent]

            # check if the resourceId is cached
            if resourceId not in resourceAccessCache:
                # if the resourceId is not cached, check for permission "level"
                # and set the cache
                resource = self.model(self.resource_coll).load(resourceId, force=True)
                resourceAccessCache[resourceId] = self.model(self.resource_coll).hasAccess(
                    resource, user=user, level=level)

            return resourceAccessCache[resourceId]

        endIndex = offset + limit if limit else None
        filteredCursor = six.moves.filter(hasAccess, cursor)
        for result in itertools.islice(filteredCursor, offset, endIndex):
            for key in removeKeys:
                if key in result:
                    del result[key]
            yield result
