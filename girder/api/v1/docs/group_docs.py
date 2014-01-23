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
    'path': '/group',
    'resource': 'group',
    'operations': [{
        'httpMethod': 'GET',
        'nickname': 'findGroups',
        'responseClass': 'Group',
        'summary': 'Search for groups or list all groups.',
        'parameters': [
            Describe.param(
                'text', "Pass this to perform a full-text search for groups.",
                required=False),
            Describe.param(
                'limit', "Result set size limit (default=50).", required=False,
                dataType='int'),
            Describe.param(
                'offset', "Offset into result set (default=0).", required=False,
                dataType='int'),
            Describe.param(
                'sort', "Field to sort the group list by (default=name)",
                required=False),
            Describe.param(
                'sortdir', "1 for ascending, -1 for descending (default=1)",
                required=False, dataType='int')
            ],
        'errorResponses': [
            Describe.errorResponse()
            ]
        }, {
        'httpMethod': 'POST',
        'nickname': 'createGroup',
        'responseClass': 'Group',
        'summary': 'Create a new group.',
        'notes': 'Must be logged in.',
        'parameters': [
            Describe.param('name', "Name of the group, must be unique."),
            Describe.param('description', "Description of the group.",
                           required=False),
            Describe.param(
                'public', "If the group should be public or private. By "
                "default, it will be private.",
                required=False, dataType='boolean')
            ],
        'errorResponses': [
            Describe.errorResponse(),
            Describe.errorResponse('Write access was denied on the parent', 403)
            ]
        }]
    })

apis.append({
    'path': '/group/{groupId}',
    'resource': 'group',
    'operations': [{
        'httpMethod': 'GET',
        'nickname': 'getGroupById',
        'responseClass': 'Group',
        'summary': 'Get a group by ID.',
        'parameters': [
            Describe.param(
                'groupId', 'The ID of the group.', paramType='path')
            ],
        'errorResponses': [
            Describe.errorResponse('ID was invalid.'),
            Describe.errorResponse(
                'Read access was denied for the group.', 403)
            ]
        }, {
        'httpMethod': 'PUT',
        'nickname': 'updateGroupById',
        'summary': 'Update a group by ID.',
        'parameters': [
            Describe.param(
                'groupId', 'The ID of the group.', paramType='path'),
            Describe.param(
                'name', 'The name to set on the group.', required=False),
            Describe.param(
                'description', 'The description to set on the group.',
                required=False),
            Describe.param(
                'public', 'Whether group should be publicly visible',
                dataType='boolean', required=False)
            ],
        'errorResponses': [
            Describe.errorResponse(),
            Describe.errorResponse(
                'Write access was denied for the group.', 403)
            ]
        }, {
        'httpMethod': 'DELETE',
        'nickname': 'deleteGroupById',
        'summary': 'Delete a group by ID.',
        'parameters': [
            Describe.param(
                'groupId', 'The ID of the group.', paramType='path')
            ],
        'errorResponses': [
            Describe.errorResponse('ID was invalid.'),
            Describe.errorResponse(
                'Admin access was denied for the group.', 403)
            ]
        }]
    })

apis.append({
    'path': '/group/{groupId}/invitation',
    'resource': 'group',
    'operations': [{
        'httpMethod': 'GET',
        'nickname': 'showInvitations',
        'responseClass': 'Group',
        'summary': 'Show outstanding invitations for a group.',
        'parameters': [
            Describe.param(
                'groupId', 'The ID of the group.', paramType='path'),
            Describe.param(
                'limit', "Result set size limit (default=50).", required=False,
                dataType='int'),
            Describe.param(
                'offset', "Offset into result set (default=0).", required=False,
                dataType='int'),
            Describe.param(
                'sort', "Field to sort the invitee list by (default=lastName)",
                required=False),
            Describe.param(
                'sortdir', "1 for ascending, -1 for descending (default=1)",
                required=False, dataType='int')
            ],
        'errorResponses': [
            Describe.errorResponse(),
            Describe.errorResponse(
                'Write access was denied for the group.', 403)
            ]
        }, {
        'httpMethod': 'POST',
        'nickname': 'inviteToGroup',
        'responseClass': 'Group',
        'summary': "Invite a user to join a group, or accept a user's request "
                   " to join.",
        'parameters': [
            Describe.param(
                'groupId', 'The ID of the group.', paramType='path'),
            Describe.param('userId', 'The ID of the user to invite or accept.'),
            Describe.param('level', 'The access level the user will be given '
                           'when they accept the invitation. Defaults to read '
                           'access (0).', required=False, dataType='int')
            ],
        'errorResponses': [
            Describe.errorResponse(),
            Describe.errorResponse(
                'Write access was denied for the group.', 403)
            ]
        }]
    })

apis.append({
    'path': '/group/{groupId}/member',
    'resource': 'group',
    'operations': [{
        'httpMethod': 'GET',
        'nickname': 'getGroupMembers',
        'responseClass': 'Group',
        'summary': 'List members of a group.',
        'parameters': [
            Describe.param(
                'groupId', 'The ID of the group.', paramType='path'),
            Describe.param(
                'limit', "Result set size limit (default=50).", required=False,
                dataType='int'),
            Describe.param(
                'offset', "Offset into result set (default=0).", required=False,
                dataType='int'),
            Describe.param(
                'sort', "Field to sort the member list by (default=lastName)",
                required=False),
            Describe.param(
                'sortdir', "1 for ascending, -1 for descending (default=1)",
                required=False, dataType='int')
            ],
        'errorResponses': [
            Describe.errorResponse('ID was invalid.'),
            Describe.errorResponse(
                'You were not invited to this group.', 403)
            ]
        }, {
        'httpMethod': 'POST',
        'nickname': 'joinGroup',
        'responseClass': 'Group',
        'summary': 'Request to join a group, or accept an invitation to join.',
        'parameters': [
            Describe.param(
                'groupId', 'The ID of the group.', paramType='path')
            ],
        'errorResponses': [
            Describe.errorResponse('ID was invalid.'),
            Describe.errorResponse(
                'You were not invited to this group, or do not have '
                'read access to it.', 403)
            ]
        }, {
        'httpMethod': 'DELETE',
        'nickname': 'removeFromGroup',
        'responseClass': 'Group',
        'summary': 'Remove yourself or another user from a group.',
        'parameters': [
            Describe.param(
                'groupId', 'The ID of the group.', paramType='path'),
            Describe.param(
                'userId', 'The ID of the user to remove. If not passed, will '
                'remove yourself from the group.', required=False)
            ],
        'errorResponses': [
            Describe.errorResponse(),
            Describe.errorResponse(
                "You don't have permission to remove that user.", 403)
            ]
        }]
    })

apis.append({
    'path': '/group/{groupId}/moderator',
    'resource': 'group',
    'operations': [{
        'httpMethod': 'POST',
        'nickname': 'promoteToModerator',
        'responseClass': 'Group',
        'summary': 'Promote a user to a moderator.',
        'parameters': [
            Describe.param(
                'groupId', 'The ID of the group.', paramType='path'),
            Describe.param(
                'userId', 'The ID of the user to promote.')
            ],
        'errorResponses': [
            Describe.errorResponse('ID was invalid.'),
            Describe.errorResponse(
                "You don't have permission to promote users.", 403)
            ]
        }, {
        'httpMethod': 'DELETE',
        'nickname': 'demoteModerator',
        'responseClass': 'Group',
        'summary': 'Demote a group moderator to a normal member.',
        'parameters': [
            Describe.param(
                'groupId', 'The ID of the group.', paramType='path'),
            Describe.param(
                'userId', 'The ID of the user to demote.')
            ],
        'errorResponses': [
            Describe.errorResponse(),
            Describe.errorResponse(
                "You don't have permission to demote users.", 403)
            ]
        }]
    })

apis.append({
    'path': '/group/{groupId}/admin',
    'resource': 'group',
    'operations': [{
        'httpMethod': 'POST',
        'nickname': 'promoteToAdmin',
        'responseClass': 'Group',
        'summary': 'Promote a user to an administrator.',
        'parameters': [
            Describe.param(
                'groupId', 'The ID of the group.', paramType='path'),
            Describe.param(
                'userId', 'The ID of the user to promote.')
            ],
        'errorResponses': [
            Describe.errorResponse('ID was invalid.'),
            Describe.errorResponse(
                "You don't have permission to promote users.", 403)
            ]
        }, {
        'httpMethod': 'DELETE',
        'nickname': 'demoteAdmin',
        'responseClass': 'Group',
        'summary': 'Demote a group admin to a normal member.',
        'parameters': [
            Describe.param(
                'groupId', 'The ID of the group.', paramType='path'),
            Describe.param(
                'userId', 'The ID of the user to demote.')
            ],
        'errorResponses': [
            Describe.errorResponse(),
            Describe.errorResponse(
                "You don't have permission to demote users.", 403)
            ]
        }]
    })

apis.append({
    'path': '/group/{groupId}/access',
    'resource': 'group',
    'operations': [{
        'httpMethod': 'GET',
        'nickname': 'getGroupAccess',
        'responseClass': 'Group',
        'summary': 'Get the access control list for a group.',
        'parameters': [
            Describe.param(
                'groupId', 'The ID of the group.', paramType='path')
            ],
        'errorResponses': [
            Describe.errorResponse('ID was invalid.'),
            Describe.errorResponse(
                'Read access was denied for the group.', 403)
            ]
        }]
    })

Describe.declareApi('group', apis=apis)
