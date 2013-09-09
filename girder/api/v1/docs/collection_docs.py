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

from ..api_docs import Describe

apis = []

apis.append({
    'path': '/collection',
    'resource': 'collection',
    'operations': [{
        'httpMethod': 'GET',
        'nickname': 'findCollections',
        'responseClass': 'Collection',
        'summary': 'List or search for collections.',
        'parameters': [
            Describe.param(
                'text',
                "Pass this to perform a full text search for collections.",
                required=False),
            Describe.param(
                'limit', "Result set size limit (default=50).", required=False,
                dataType='int'),
            Describe.param(
                'offset', "Offset into result set (default=0).", required=False,
                dataType='int'),
            Describe.param(
                'sort', "Field to sort the result list by (default=name)",
                required=False),
            Describe.param(
                'sortdir', "1 for ascending, -1 for descending (default=1)",
                required=False, dataType='int')
            ]
        }, {
        'httpMethod': 'POST',
        'nickname': 'createCollection',
        'responseClass': 'Collection',
        'summary': 'Create a new collection.',
        'parameters': [
            Describe.param('name', "Name for the collection. Must be unique."),
            Describe.param('description', "Collection description.",
                           required=False),
            Describe.param('public', "Public read access flag.",
                           dataType='boolean')
            ],
        'errorResponses': [
            Describe.errorResponse(),
            Describe.errorResponse('You are not an administrator', 403)
            ]
        }]
    })

apis.append({
    'path': '/collection/{collectionId}',
    'resource': 'collection',
    'operations': [{
        'httpMethod': 'GET',
        'nickname': 'getCollectionById',
        'responseClass': 'Collection',
        'summary': 'Get a collection by ID.',
        'parameters': [
            Describe.param(
                'collectionId', 'The ID of the collection.', paramType='path')
            ],
        'errorResponses': [
            Describe.errorResponse('ID was invalid.'),
            Describe.errorResponse('You do not have permission to see this '
                                   'collection.', 403)
            ]
        }, {
        'httpMethod': 'DELETE',
        'nickname': 'deleteCollectionById',
        'responseClass': 'Collection',
        'summary': 'Delete a collection by ID.',
        'parameters': [
            Describe.param(
                'collectionId', 'The ID of the collection.', paramType='path')
            ],
        'errorResponses': [
            Describe.errorResponse('ID was invalid.'),
            Describe.errorResponse('You do not have permission to delete this '
                                   'collection.', 403)
            ]
        }]
    })

Describe.declareApi('collection', apis=apis)
