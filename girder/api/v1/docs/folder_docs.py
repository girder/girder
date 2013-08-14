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

_apis = []

_apis.append({
    'path': '/folder',
    'resource': 'user',
    'operations': [{
        'httpMethod': 'GET',
        'nickname': 'findFolders',
        'responseClass': 'Folder',
        'summary': 'Search for folders by certain properties.',
        'parameters': [
            Describe.param(
                'parentType', "Type of the folder's parent: either 'user', "
                              "'folder', or 'community' (default='folder').",
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
                dataType='int')
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
                "'folder', or 'community' (default='folder').", required=False),
            Describe.param('parentId', "The ID of the folder's parent."),
            Describe.param('name', "Name of the folder."),
            Describe.param('description', "Description of the folder.",
                           required=False),
            Describe.param(
                'public', "If the folder should be public or private. By "
                "default, inherits the value from parent folder, or in the "
                " case of user or community parentType, defaults to False.",
                required=False, dataType='boolean')
            ],
        'errorResponses': [
            Describe.errorResponse(),
            Describe.errorResponse('Write access was denied on the parent', 403)
            ]
        }]
    })

_apis.append({
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
        'responseClass': 'Folder',
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
        }]
    })

Describe.declareApi('folder', apis=_apis)
