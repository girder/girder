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
    'path': '/file',
    'resource': 'file',
    'operations': [{
        'httpMethod': 'POST',
        'nickname': 'initUpload',
        'responseClass': 'Upload',
        'summary': 'Start a new upload.',
        'parameters': [
            Describe.param(
                'parentType', "Type being uploaded into, either 'folder' or "
                "'item'."),
            Describe.param('parentId', "The ID of the parent."),
            Describe.param('name', "Name of the file being uploaded."),
            Describe.param('size', "Size in bytes of the file.",
                           dataType='integer'),
            Describe.param('mimeType', "The MIME type of the file.",
                           required=False)
            ],
        'errorResponses': [
            Describe.errorResponse(),
            Describe.errorResponse('Write access was denied on the parent', 403)
            ]
        }]
    })

apis.append({
    'path': '/file/{fileId}',
    'resource': 'file',
    'operations': [{
        'httpMethod': 'GET',
        'nickname': 'getFileById',
        'responseClass': 'File',
        'summary': 'Get a file by ID.',
        'parameters': [
            Describe.param(
                'fileId', 'The ID of the file.', paramType='path')
            ],
        'errorResponses': [
            Describe.errorResponse('ID was invalid.'),
            Describe.errorResponse(
                'Read access was denied for the containing folder.', 403)
            ]
        }, {
        'httpMethod': 'DELETE',
        'nickname': 'deleteFileById',
        'summary': 'Delete a file by ID.',
        'parameters': [
            Describe.param(
                'fileId', 'The ID of the file.', paramType='path')
            ],
        'errorResponses': [
            Describe.errorResponse('ID was invalid.'),
            Describe.errorResponse(
                'Admin access was denied for the containing folder.', 403)
            ]
        }]
    })

apis.append({
    'path': '/file/{fileId}/download',
    'resource': 'file',
    'operations': [{
        'httpMethod': 'GET',
        'nickname': 'downloadFile',
        'summary': 'Download a file.',
        'parameters': [
            Describe.param(
                'fileId', 'The ID of the file.', paramType='path')
            ],
        'errorResponses': [
            Describe.errorResponse('ID was invalid.'),
            Describe.errorResponse(
                'Read access was denied for the containing folder.', 403)
            ]
        }]
    })

apis.append({
    'path': '/file/chunk',
    'resource': 'file',
    'operations': [{
        'httpMethod': 'POST',
        'nickname': 'uploadChunk',
        'summary': 'Upload a chunk of a file with multipart/form-data.',
        'parameters': [
            Describe.param('uploadId', 'The ID of the upload record.'),
            Describe.param('offset', 'Offset of the chunk in the file.',
                           dataType='integer'),
            Describe.param('chunk', 'The actual bytes of the chunk.',
                           dataType='byte')
            ],
        'errorResponses': [
            Describe.errorResponse('ID was invalid.'),
            Describe.errorResponse(
                'You are not the same user who initiated the upload.', 403)
            ]
        }]
    })

apis.append({
    'path': '/file/offset',
    'resource': 'file',
    'operations': [{
        'httpMethod': 'GET',
        'nickname': 'uploadChunk',
        'summary': 'Request required offset before resuming an upload.',
        'parameters': [
            Describe.param('uploadId', 'The ID of the upload record.')
            ],
        'errorResponses': [
            Describe.errorResponse('ID was invalid, or the offset did not match'
                                   ' the server record.')
            ]
        }]
    })

Describe.declareApi('file', apis=apis)
