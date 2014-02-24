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
    'path': '/item',
    'resource': 'item',
    'operations': [{
        'httpMethod': 'GET',
        'nickname': 'findItems',
        'responseClass': 'Item',
        'summary': 'Search for items by certain properties.',
        'parameters': [
            Describe.param(
                'folderId', "Pass this to get the list of all items in a "
                "single folder.", required=False),
            Describe.param(
                'text', "Pass this to perform a full text search for items.",
                required=False),
            Describe.param(
                'limit', "Result set size limit (default=50).", required=False,
                dataType='int'),
            Describe.param(
                'offset', "Offset into result set (default=0).", required=False,
                dataType='int'),
            Describe.param(
                'sort', "Field to sort the item list by (default=name)",
                required=False),
            Describe.param(
                'sortdir', "1 for ascending, -1 for descending (default=1)",
                required=False, dataType='int')
            ],
        'errorResponses': [
            Describe.errorResponse(),
            Describe.errorResponse(
                'Read access was denied on the parent folder.', 403)
            ]
        }, {
        'httpMethod': 'POST',
        'nickname': 'createItem',
        'responseClass': 'Item',
        'summary': 'Create a new item.',
        'parameters': [
            Describe.param('folderId', "The ID of the parent folder."),
            Describe.param('name', "Name for the item."),
            Describe.param('description', "Description for the item.",
                           required=False)
            ],
        'errorResponses': [
            Describe.errorResponse(),
            Describe.errorResponse('Write access was denied on the parent '
                                   'folder.', 403)
            ]
        }]
    })

apis.append({
    'path': '/item/{itemId}',
    'resource': 'item',
    'operations': [{
        'httpMethod': 'GET',
        'nickname': 'getItemById',
        'responseClass': 'Item',
        'summary': 'Get an item by ID.',
        'parameters': [
            Describe.param(
                'itemId', 'The ID of the item.', paramType='path')
            ],
        'errorResponses': [
            Describe.errorResponse('ID was invalid.'),
            Describe.errorResponse(
                'Read access was denied for the item.', 403)
            ]
        }, {
        'httpMethod': 'PUT',
        'nickname': 'editItemById',
        'responseClass': 'Item',
        'summary': 'Edit an item by ID.',
        'parameters': [
            Describe.param(
                'itemId', 'The ID of the item.', paramType='path'),
            Describe.param('name', "Name for the item.",
                           required=False),
            Describe.param('description', "Item description.",
                           required=False),
            ],
        'errorResponses': [
            Describe.errorResponse('ID was invalid.'),
            Describe.errorResponse(
                'Write access was denied for the item.', 403)
            ]
        }, {
        'httpMethod': 'DELETE',
        'nickname': 'deleteItemById',
        'summary': 'Delete an item by ID.',
        'parameters': [
            Describe.param(
                'itemId', 'The ID of the item.', paramType='path')
            ],
        'errorResponses': [
            Describe.errorResponse('ID was invalid.'),
            Describe.errorResponse(
                'Admin access was denied for the item.', 403)
            ]
        }]
    })

apis.append({
    'path': '/item/{itemId}/files',
    'resource': 'item',
    'operations': [{
        'httpMethod': 'GET',
        'nickname': 'getFileByItemId',
        'responseClass': 'File',
        'summary': 'Get the files associated with an item by its ID.',
        'parameters': [
            Describe.param(
                'itemId', 'The ID of the item.', paramType='path'),
            Describe.param(
                'limit', "Result set size limit (default=50).", required=False,
                dataType='int'),
            Describe.param(
                'offset', "Offset into result set (default=0).", required=False,
                dataType='int'),
            Describe.param(
                'sort', "Field to sort the result list by (default=name)",
                required=False)
            ],
        'errorResponses': [
            Describe.errorResponse('ID was invalid.'),
            Describe.errorResponse(
                'Read access was denied for the item.', 403)
            ]
        }]
    })

apis.append({
    'path': '/item/{itemId}/download',
    'resource': 'item',
    'operations': [{
        'httpMethod': 'GET',
        'nickname': 'getItemDownoad',
        'responseClass': 'File',
        'summary': 'Download an item',
        'parameters': [
            Describe.param(
                'itemId', 'The ID of the item.', paramType='path')
            ],
        'errorResponses': [
            Describe.errorResponse('ID was invalid.'),
            Describe.errorResponse(
                'Read access was denied for the item.', 403)
            ]
        }]
    })

apis.append({
    'path': '/item/{itemId}/metadata',
    'resource': 'item',
    'operations': [{
        'httpMethod': 'PUT',
        'nickname': 'putItemMetadata',
        'responseClass': 'Item',
        'summary': 'Set metadata on an item',
        'notes': 'Set metadata fields to null in order to delete them.',
        'parameters': [
            Describe.param(
                'itemId', 'The ID of the item.', paramType='path'),
            Describe.param(
                'body', 'A JSON object containing the metadata keys to add',
                required=True, paramType='body')
            ],
        'errorResponses': [
            Describe.errorResponse('ID was invalid.'),
            Describe.errorResponse(
                'Write access was denied for the item.', 403)
            ]
        }]
    })

Describe.declareApi('item', apis=apis)
