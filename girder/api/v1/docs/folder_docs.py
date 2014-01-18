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
    'path': '/folder',
    'resource': 'folder',
    'operations': [{
        'httpMethod': 'GET',
        'nickname': 'findFolders',
        'responseClass': 'Folder',
        'summary': 'Search for folders by certain properties.',
        'parameters': [
            Describe.param(
                'parentType', "Type of the folder's parent: either 'user', "
                              "'folder', or 'collection' (default='folder').",
                              required=False),
            Describe.param(
                'parentId', "The ID of the folder's parent.", required=False),
            Describe.param(
                'text', "Pass a full text search query.", required=False),
            Describe.param(
                'limit', "Result set size limit (default=50).", required=False,
                dataType='int'),
            Describe.param(
                'offset', "Offset into result set (default=0).", required=False,
                dataType='int'),
            Describe.param(
                'sort', "Field to sort the folder list by (default=name)",
                required=False),
            Describe.param(
                'sortdir', "1 for ascending, -1 for descending (default=1)",
                required=False, dataType='int')
            ],
        'errorResponses': [
            Describe.errorResponse(),
            Describe.errorResponse(
                'Read access was denied on the parent resource.', 403)
            ]
        }, {
        'httpMethod': 'POST',
        'nickname': 'createFolder',
        'responseClass': 'Folder',
        'summary': 'Create a new folder.',
        'parameters': [
            Describe.param(
                'parentType', "Type of the folder's parent: either 'user', "
                "'folder', or 'collection' (default='folder').",
                required=False),
            Describe.param('parentId', "The ID of the folder's parent."),
            Describe.param('name', "Name of the folder."),
            Describe.param('description', "Description of the folder.",
                           required=False),
            Describe.param(
                'public', "If the folder should be public or private. By "
                "default, inherits the value from parent folder, or in the "
                " case of user or collection parentType, defaults to False.",
                required=False, dataType='boolean')
            ],
        'errorResponses': [
            Describe.errorResponse(),
            Describe.errorResponse('Write access was denied on the parent', 403)
            ]
        }]
    })

apis.append({
    'path': '/folder/{folderId}',
    'resource': 'folder',
    'operations': [{
        'httpMethod': 'GET',
        'nickname': 'getFolderById',
        'responseClass': 'Folder',
        'summary': 'Get a folder by ID.',
        'parameters': [
            Describe.param(
                'folderId', 'The ID of the folder.', paramType='path')
            ],
        'errorResponses': [
            Describe.errorResponse('ID was invalid.'),
            Describe.errorResponse(
                'Read access was denied for the folder.', 403)
            ]
        }, {
        'httpMethod': 'DELETE',
        'nickname': 'deleteFolderById',
        'summary': 'Delete a folder by ID.',
        'parameters': [
            Describe.param(
                'folderId', 'The ID of the folder.', paramType='path')
            ],
        'errorResponses': [
            Describe.errorResponse('ID was invalid.'),
            Describe.errorResponse(
                'Admin access was denied for the folder.', 403)
            ]
        },  {
        'httpMethod': 'PUT',
        'nickname': 'updateFolderById',
        'summary': 'Update a folder by ID.',
        'parameters': [
            Describe.param(
                'folderId', 'The ID of the folder.', paramType='path'),
            Describe.param('name', "Name of the folder."),
            Describe.param('description', "Description of the folder.",
                           required=False),
            Describe.param(
                'public', "If the folder should be public or private.",
                required=False, dataType='boolean')
            ],
        'errorResponses': [
            Describe.errorResponse('ID was invalid.'),
            Describe.errorResponse(
                'Write access was denied for the folder.', 403)
            ]
        }]
    })

apis.append({
    'path': '/folder/{folderId}/access',
    'resource': 'folder',
    'operations': [{
        'httpMethod': 'GET',
        'nickname': 'getFolderAccess',
        'responseClass': 'Folder',
        'summary': 'Get the access control list for a folder.',
        'parameters': [
            Describe.param(
                'folderId', 'The ID of the folder.', paramType='path')
            ],
        'errorResponses': [
            Describe.errorResponse('ID was invalid.'),
            Describe.errorResponse(
                'Admin access was denied for the folder.', 403)
            ]
        }, {
        'httpMethod': 'PUT',
        'nickname': 'updateFolderAccess',
        'summary': 'Update the access control list for a folder.',
        'parameters': [
            Describe.param(
                'folderId', 'The ID of the folder.', paramType='path'),
            Describe.param(
                'access', 'The JSON-encoded access control list.'),
            Describe.param(
                'public', 'Public access flag.', dataType='bool')
            ],
        'errorResponses': [
            Describe.errorResponse('ID was invalid.'),
            Describe.errorResponse(
                'Admin access was denied for the folder.', 403)
            ]
        }]
    })

apis.append({
    'path': '/folder/{folderId}/download',
    'resource': 'folder',
    'operations': [{
        'httpMethod': 'GET',
        'nickname': 'downloadFolder',
        'responseClass': 'Folder',
        'summary': 'Download an entire folder as a zip archive.',
        'parameters': [
            Describe.param(
                'folderId', 'The ID of the folder.', paramType='path')
            ],
        'errorResponses': [
            Describe.errorResponse('ID was invalid.'),
            Describe.errorResponse(
                'Read access was denied for the folder.', 403)
            ]
        }]
    })

Describe.declareApi('folder', apis=apis)
