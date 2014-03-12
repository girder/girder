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

import json

from .docs import folder_docs
from ..rest import Resource as BaseResource, RestException
from ...constants import AccessType
from ...utility import ziputil


class Resource(BaseResource):
    """
    API Endpoints that deal with operations across multiple resource types.
    """
    def __init__(self):
        self.route('GET', ('search',), self.search)

    def search(self, params):
        """
        This endpoint can be used to text search against multiple different
        model types at once.
        :param q: The search query string.
        :param types: A JSON list of types to search.
        :type types: str
        :param limit: The result limit per type. Defaults to 10.
        """
        self.requireParams(('q', 'types'), params)
        user = self.getCurrentUser()

        limit = int(params.get('limit', 10))

        results = {}
        try:
            types = json.loads(params['types'])
        except ValueError:
            raise RestException('The types parameter must be JSON.')

        if 'item' in types:
            tempResults = self.model('item').textSearch(params['q'],
                                                        {'name': 1})
            results['item'] = [it['obj'] for it in tempResults]

        if 'collection' in types:
            results['collection'] = self.model('collection').textSearch(
                params['q'], user=user, limit=limit, project={
                    'name': 1
                })
        if 'folder' in types:
            results['folder'] = self.model('folder').textSearch(
                params['q'], user=user, limit=limit, project={
                    'name': 1
                })
        if 'group' in types:
            results['group'] = self.model('group').textSearch(
                params['q'], user=user, limit=limit, project={
                    'name': 1
                })
        if 'user' in types:
            results['user'] = self.model('user').textSearch(
                params['q'], user=user, limit=limit, project={
                    'firstName': 1,
                    'lastName': 1,
                    'login': 1
                })
        return results
