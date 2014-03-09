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

from .. import describe
from ..rest import Resource, RestException, loadmodel
from ...models.model_base import ValidationException, AccessException
from ...constants import AccessType


class Group(Resource):
    """API Endpoint for groups."""
    def __init__(self):
        self.route('DELETE', (':id',), self.deleteGroup)
        self.route('DELETE', (':id', 'member'), self.removeFromGroup)
        self.route('DELETE', (':id', 'moderator'), self.demote)
        self.route('DELETE', (':id', 'admin'), self.demote)
        self.route('GET', (), self.find)
        self.route('GET', (':id',), self.getGroup)
        self.route('GET', (':id', 'access'), self.getGroupAccess)
        self.route('GET', (':id', 'invitation'), self.getGroupInvitations)
        self.route('GET', (':id', 'member'), self.listMembers)
        self.route('POST', (), self.createGroup)
        self.route('POST', (':id', 'invitation'), self.inviteToGroup)
        self.route('POST', (':id', 'member'), self.joinGroup)
        self.route('POST', (':id', 'moderator'), self.promoteToModerator)
        self.route('POST', (':id', 'admin'), self.promoteToAdmin)
        self.route('PUT', (':id',), self.updateGroup)

    def _filter(self, group, accessList=False, requests=False):
        """
        Filter a group document for display to the user.

        :param group: The document to filter.
        :type group: dict
        :param user: The current user.
        :type user: dict
        :param accessList: Whether to include the access control list field.
        :type accessList: bool
        :param requests: Whether to include the requests list field.
        :type requests: bool
        :returns: The filtered group document.
        """
        keys = ['_id', 'name', 'public', 'description', 'created', 'updated']
        user = self.getCurrentUser()

        if requests:
            keys.append('requests')

        accessLevel = self.model('group').getAccessLevel(group, user)

        if accessList:
            keys.append('access')

        group = self.filterDocument(group, allow=keys)
        group['_accessLevel'] = accessLevel

        if accessList:
            group['access'] = self.model('group').getFullAccessList(group)

        if requests:
            group['requests'] = self.model('group').getFullRequestList(group)

        return group

    def find(self, params):
        """
        List or search for groups.

        :param params: Request query parameters.
        :type params: dict
        :returns: A page of matching Group documents.
        """
        limit, offset, sort = self.getPagingParameters(params, 'name')

        user = self.getCurrentUser()

        return [self._filter(group) for group in self.model('group').list(
            user=user, offset=offset, limit=limit, sort=sort)]
    find.description = {
        'summary': 'Search for groups or list all groups.',
        'parameters': [
            describe.param(
                'text', "Pass this to perform a full-text search for groups.",
                required=False),
            describe.param(
                'limit', "Result set size limit (default=50).", required=False,
                dataType='int'),
            describe.param(
                'offset', "Offset into result set (default=0).", required=False,
                dataType='int'),
            describe.param(
                'sort', "Field to sort the group list by (default=name)",
                required=False),
            describe.param(
                'sortdir', "1 for ascending, -1 for descending (default=1)",
                required=False, dataType='int')
        ],
        'errorResponses': [
            describe.errorResponse()
        ]
    }

    def createGroup(self, params):
        """
        Create a new group.

        :param params: Request query parameters.
        :type params: dict
        :returns: The created group document.
        """
        self.requireParams(('name',), params)

        name = params['name'].strip()
        description = params.get('description', '').strip()
        public = params.get('public', '').lower() == 'true'

        user = self.getCurrentUser()

        if user is None:
            raise AccessException('Must be logged in to create a group.')

        group = self.model('group').createGroup(
            name=name, creator=user, description=description, public=public)

        return self._filter(group)
    createGroup.description = {
        'responseClass': 'Group',
        'summary': 'Create a new group.',
        'notes': 'Must be logged in.',
        'parameters': [
            describe.param('name', "Name of the group, must be unique."),
            describe.param('description', "Description of the group.",
                           required=False),
            describe.param(
                'public', "If the group should be public or private. By "
                "default, it will be private.",
                required=False, dataType='boolean')
        ],
        'errorResponses': [
            describe.errorResponse(),
            describe.errorResponse('Write access was denied on the parent', 403)
        ]
    }

    @loadmodel(map={'id': 'group'}, model='group', level=AccessType.READ)
    def getGroup(self, group, params):
        return self._filter(group)
    getGroup.description = {
        'responseClass': 'Group',
        'summary': 'Get a group by ID.',
        'parameters': [
            describe.param(
                'id', 'The ID of the group.', paramType='path')
        ],
        'errorResponses': [
            describe.errorResponse('ID was invalid.'),
            describe.errorResponse(
                'Read access was denied for the group.', 403)
        ]
    }

    @loadmodel(map={'id': 'group'}, model='group', level=AccessType.READ)
    def getGroupAccess(self, group, params):
        return self._filter(group, accessList=True, requests=True)
    getGroupAccess.description = {
        'responseClass': 'Group',
        'summary': 'Get the access control list for a group.',
        'parameters': [
            describe.param('id', 'The ID of the group.', paramType='path')
        ],
        'errorResponses': [
            describe.errorResponse('ID was invalid.'),
            describe.errorResponse('Read access was denied for the group.', 403)
        ]
    }

    @loadmodel(map={'id': 'group'}, model='group', level=AccessType.READ)
    def getGroupInvitations(self, group, params):
        limit, offset, sort = self.getPagingParameters(params, 'lastName')
        return self.model('group').getInvites(group, limit, offset, sort)
    getGroupInvitations.description = {
        'responseClass': 'Group',
        'summary': 'Show outstanding invitations for a group.',
        'parameters': [
            describe.param(
                'id', 'The ID of the group.', paramType='path'),
            describe.param(
                'limit', "Result set size limit (default=50).", required=False,
                dataType='int'),
            describe.param(
                'offset', "Offset into result set (default=0).", required=False,
                dataType='int'),
            describe.param(
                'sort', "Field to sort the invitee list by (default=lastName)",
                required=False),
            describe.param(
                'sortdir', "1 for ascending, -1 for descending (default=1)",
                required=False, dataType='int')
        ],
        'errorResponses': [
            describe.errorResponse(),
            describe.errorResponse(
                'Read access was denied for the group.', 403)
        ]
    }

    @loadmodel(map={'id': 'group'}, model='group', level=AccessType.WRITE)
    def updateGroup(self, group, params):
        """
        Update a group.

        :returns: The updated group document.
        """
        user = self.getCurrentUser()

        public = params.get('public', 'false').lower() == 'true'
        self.model('group').setPublic(group, public)

        group['name'] = params.get('name', group['name']).strip()
        group['description'] = params.get(
            'description', group['description']).strip()

        group = self.model('group').updateGroup(group)
        return self._filter(group)
    updateGroup.description = {
        'summary': 'Update a group by ID.',
        'parameters': [
            describe.param(
                'id', 'The ID of the group.', paramType='path'),
            describe.param(
                'name', 'The name to set on the group.', required=False),
            describe.param(
                'description', 'The description to set on the group.',
                required=False),
            describe.param(
                'public', 'Whether group should be publicly visible',
                dataType='boolean', required=False)
        ],
        'errorResponses': [
            describe.errorResponse(),
            describe.errorResponse(
                'Write access was denied for the group.', 403)
        ]
    }

    @loadmodel(map={'id': 'group'}, model='group', level=AccessType.READ)
    def joinGroup(self, group, params):
        """
        Accept a group invitation. If you have not been invited, this will
        instead request an invitation.

        :param group: The group to join.
        :type group: dict
        :param user: The current user.
        :type user: dict
        :returns: The updated group document.
        """
        return self._filter(
            self.model('group').joinGroup(group, self.getCurrentUser()),
            accessList=True, requests=True)
    joinGroup.description = {
        'responseClass': 'Group',
        'summary': 'Request to join a group, or accept an invitation to join.',
        'parameters': [
            describe.param('id', 'The ID of the group.', paramType='path')
        ],
        'errorResponses': [
            describe.errorResponse('ID was invalid.'),
            describe.errorResponse(
                'You were not invited to this group, or do not have '
                'read access to it.', 403)
        ]
    }

    @loadmodel(map={'id': 'group'}, model='group', level=AccessType.READ)
    def listMembers(self, group, params):
        """
        Paginated member list of group members.

        :returns: A page of User documents representing members of the group.
        """
        limit, offset, sort = self.getPagingParameters(params, 'lastName')

        return [g for g in self.model('group').listMembers(
            group, offset=offset, limit=limit, sort=sort)]
    listMembers.description = {
        'summary': 'List members of a group.',
        'parameters': [
            describe.param(
                'id', 'The ID of the group.', paramType='path'),
            describe.param(
                'limit', "Result set size limit (default=50).", required=False,
                dataType='int'),
            describe.param(
                'offset', "Offset into result set (default=0).", required=False,
                dataType='int'),
            describe.param(
                'sort', "Field to sort the member list by (default=lastName)",
                required=False),
            describe.param(
                'sortdir', "1 for ascending, -1 for descending (default=1)",
                required=False, dataType='int')
        ],
        'errorResponses': [
            describe.errorResponse('ID was invalid.'),
            describe.errorResponse('Read access was denied for the group.', 403)
        ]
    }

    @loadmodel(map={'id': 'group'}, model='group', level=AccessType.WRITE)
    def inviteToGroup(self, group, params):
        """Invite the user to join the group."""
        self.requireParams(('userId',), params)
        user = self.getCurrentUser()
        level = int(params.get('level', AccessType.READ))

        userToInvite = self.model('user').load(
            id=params['userId'], user=user, level=AccessType.READ, exc=True)

        # Can only invite into access levels that you yourself have
        self.model('group').requireAccess(group, user, level)
        self.model('group').inviteUser(group, userToInvite, level)

        return self._filter(group, accessList=True, requests=True)
    inviteToGroup.description = {
        'responseClass': 'Group',
        'summary': "Invite a user to join a group, or accept a user's request "
                   " to join.",
        'parameters': [
            describe.param('id', 'The ID of the group.', paramType='path'),
            describe.param('userId', 'The ID of the user to invite or accept.'),
            describe.param('level', 'The access level the user will be given '
                           'when they accept the invitation. Defaults to read '
                           'access (0).', required=False, dataType='int')
        ],
        'errorResponses': [
            describe.errorResponse(),
            describe.errorResponse(
                'Write access was denied for the group.', 403)
        ]
    }

    @loadmodel(map={'id': 'group'}, model='group', level=AccessType.ADMIN)
    def promoteToModerator(self, group, params):
        return self._promote(group, params, AccessType.WRITE)
    promoteToModerator.description = {
        'responseClass': 'Group',
        'summary': 'Promote a member to be a moderator of the group.',
        'parameters': [
            describe.param('id', 'The ID of the group.', paramType='path'),
            describe.param('userId', 'The ID of the user to promote.')
        ],
        'errorResponses': [
            describe.errorResponse('ID was invalid.'),
            describe.errorResponse(
                "You don't have permission to promote users.", 403)
        ]
    }

    @loadmodel(map={'id': 'group'}, model='group', level=AccessType.ADMIN)
    def promoteToAdmin(self, group, params):
        return self._promote(group, params, AccessType.ADMIN)
    promoteToAdmin.description = {
        'responseClass': 'Group',
        'summary': 'Promote a member to be an administrator of the group.',
        'parameters': [
            describe.param('id', 'The ID of the group.', paramType='path'),
            describe.param('userId', 'The ID of the user to promote.')
        ],
        'errorResponses': [
            describe.errorResponse('ID was invalid.'),
            describe.errorResponse(
                "You don't have permission to promote users.", 403)
        ]
    }

    def _promote(self, group, params, level):
        """
        Promote a user to moderator or administrator.
        :param group: The group to promote within.
        :param params: Request parameters.
        :param level: Either WRITE or ADMIN, for moderator or administrator.
        :type level: AccessType
        :returns: The updated group document.
        """
        self.requireParams(('userId',), params)
        user = self.getCurrentUser()

        userToPromote = self.model('user').load(
            id=params['userId'], user=user, level=AccessType.READ, exc=True)

        if not group['_id'] in userToPromote.get('groups', []):
            raise AccessException('That user is not a group member.')

        group = self.model('group').setUserAccess(
            group, userToPromote, level=level, save=True)
        return self._filter(group, accessList=True)

    @loadmodel(map={'id': 'group'}, model='group', level=AccessType.ADMIN)
    def demote(self, group, params):
        """
        Demote a user down to a normal member.

        :returns: The updated group document.
        """
        self.requireParams(('userId',), params)
        user = self.getCurrentUser()

        userToDemote = self.model('user').load(
            id=params['userId'], user=user, level=AccessType.READ, exc=True)

        group = self.model('group').setUserAccess(
            group, userToDemote, level=AccessType.READ, save=True)
        return self._filter(group, accessList=True, requests=True)
    demote.description = {
        'responseClass': 'Group',
        'summary': 'Demote a user to a normal group member.',
        'parameters': [
            describe.param('id', 'The ID of the group.', paramType='path'),
            describe.param('userId', 'The ID of the user to demote.')
        ],
        'errorResponses': [
            describe.errorResponse(),
            describe.errorResponse(
                "You don't have permission to demote users.", 403)
        ]
    }

    @loadmodel(map={'id': 'group'}, model='group', level=AccessType.READ)
    def removeFromGroup(self, group, params):
        """
        Remove a user from a group. Pass a 'userId' key in params to
        remove a specific user; otherwise will remove this user.

        :param group: The group to remove the user from.
        :type group: dict
        :param user: The current user (not the user being removed).
        :type user: dict
        :param params: Request query parameters.
        :type params: dict
        :returns: The updated group document.
        """
        user = self.getCurrentUser()

        if 'userId' in params:
            userToRemove = self.model('user').load(
                id=params['userId'], user=user, level=AccessType.READ, exc=True)
        else:
            # Assume user is removing himself from the group
            userToRemove = user

        # If removing someone else, you must have at least as high an
        # access level as they do, and you must have at least write access
        # to remove any user other than yourself.
        if user['_id'] != userToRemove['_id']:
            if self.model('group').hasAccess(group, userToRemove,
                                             AccessType.ADMIN):
                self.model('group').requireAccess(group, user, AccessType.ADMIN)
            else:
                self.model('group').requireAccess(group, user, AccessType.WRITE)

        return self._filter(
            self.model('group').removeUser(group, userToRemove), requests=True,
            accessList=True)
    removeFromGroup.description = {
        'responseClass': 'Group',
        'summary': 'Remove a user from a group, or uninvite them.',
        'notes': 'If the specified user is not yet a member of the group, this'
                 ' will delete any oustanding invitation or membership request'
                 ' for the user. Passing no userId parameter will assume that'
                 ' the current user is removing himself.',
        'parameters': [
            describe.param('id', 'The ID of the group.', paramType='path'),
            describe.param(
                'userId', 'The ID of the user to remove. If not passed, will '
                'remove yourself from the group.', required=False)
        ],
        'errorResponses': [
            describe.errorResponse(),
            describe.errorResponse(
                "You don't have permission to remove that user.", 403)
        ]
    }

    @loadmodel(map={'id': 'group'}, model='group', level=AccessType.ADMIN)
    def deleteGroup(self, group, params):
        self.model('group').remove(group)
        return {'message': 'Deleted the group {}.'.format(group['name'])}
    deleteGroup.description = {
        'summary': 'Delete a group by ID.',
        'parameters': [
            describe.param(
                'id', 'The ID of the group.', paramType='path')
        ],
        'errorResponses': [
            describe.errorResponse('ID was invalid.'),
            describe.errorResponse(
                'Admin access was denied for the group.', 403)
        ]
    }
