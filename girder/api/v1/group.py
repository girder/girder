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

from ..describe import Description
from ..rest import Resource, loadmodel
from girder.models.model_base import AccessException
from girder.constants import AccessType
from girder.utility import mail_utils
from girder.api import access


class Group(Resource):
    """API Endpoint for groups."""
    def __init__(self):
        self.resourceName = 'group'
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

    @access.public
    def find(self, params):
        """
        List or search for groups.

        :param params: Request query parameters.
        :type params: dict
        :returns: A page of matching Group documents.
        """
        limit, offset, sort = self.getPagingParameters(params, 'name')
        user = self.getCurrentUser()
        if 'text' in params:
            exact = self.boolParam('exact', params, default=False)
            if not exact:
                groupList = self.model('group').textSearch(
                    params['text'], user=user, offset=offset, limit=limit,
                    sort=sort)
            else:
                groupList = self.model('group').find(
                    {'name': params['text']}, offset=offset, limit=limit,
                    sort=sort)
        else:
            groupList = self.model('group').list(user=user, offset=offset,
                                                 limit=limit, sort=sort)
        return [self.model('group').filter(group, user) for group in groupList]
    find.description = (
        Description('Search for groups or list all groups.')
        .param('text', "Pass this to perform a full-text search for groups.",
               required=False)
        .param('limit', "Result set size limit (default=50).", required=False,
               dataType='int')
        .param('offset', "Offset into result set (default=0).", required=False,
               dataType='int')
        .param('sort', "Field to sort the group list by (default=name)",
               required=False)
        .param('sortdir', "1 for ascending, -1 for descending (default=1)",
               required=False, dataType='int')
        .param('exact', 'If true, only return exact name matches.  This is '
               'case sensitive.', required=False, dataType='boolean')
        .errorResponse())

    @access.user
    def createGroup(self, params):
        """
        Create a new group.

        :param params: Request query parameters.
        :type params: dict
        :returns: The created group document.
        """
        self.requireParams('name', params)

        name = params['name'].strip()
        description = params.get('description', '').strip()
        public = self.boolParam('public', params, default=False)

        user = self.getCurrentUser()

        group = self.model('group').createGroup(
            name=name, creator=user, description=description, public=public)

        return self.model('group').filter(group, user)
    createGroup.description = (
        Description('Create a new group.')
        .responseClass('Group')
        .notes('Must be logged in.')
        .param('name', 'Unique name for the group.')
        .param('description', 'Description of the group.', required=False)
        .param('public', """Whether the group should be publicly visible. The
               default is private.""", required=False, dataType='boolean')
        .errorResponse()
        .errorResponse('Write access was denied on the parent', 403))

    @access.public
    @loadmodel(model='group', level=AccessType.READ)
    def getGroup(self, group, params):
        user = self.getCurrentUser()
        return self.model('group').filter(group, user)
    getGroup.description = (
        Description('Get a group by ID.')
        .responseClass('Group')
        .param('id', 'The ID of the group.', paramType='path')
        .errorResponse('ID was invalid.')
        .errorResponse('Read access was denied for the group.', 403))

    @access.public
    @loadmodel(model='group', level=AccessType.READ)
    def getGroupAccess(self, group, params):
        user = self.getCurrentUser()
        return self.model('group').filter(group, user, accessList=True,
                                          requests=True)
    getGroupAccess.description = (
        Description('Get the access control list for a group.')
        .responseClass('Group')
        .param('id', 'The ID of the group.', paramType='path')
        .errorResponse('ID was invalid.')
        .errorResponse('Read access was denied for the group.', 403))

    @access.public
    @loadmodel(model='group', level=AccessType.READ)
    def getGroupInvitations(self, group, params):
        limit, offset, sort = self.getPagingParameters(params, 'lastName')
        return list(self.model('group').getInvites(group, limit, offset, sort))
    getGroupInvitations.description = (
        Description('Show outstanding invitations for a group.')
        .responseClass('Group')
        .param('id', 'The ID of the group.', paramType='path')
        .param('limit', "Result set size limit (default=50).", required=False,
               dataType='int')
        .param('offset', "Offset into result set (default=0).", required=False,
               dataType='int')
        .param('sort', "Field to sort the invitee list by (default=lastName)",
               required=False)
        .param('sortdir', "1 for ascending, -1 for descending (default=1)",
               required=False, dataType='int')
        .errorResponse()
        .errorResponse('Read access was denied for the group.', 403))

    @access.user
    @loadmodel(model='group', level=AccessType.WRITE)
    def updateGroup(self, group, params):
        user = self.getCurrentUser()

        public = self.boolParam('public', params, default=False)
        self.model('group').setPublic(group, public)

        group['name'] = params.get('name', group['name']).strip()
        group['description'] = params.get(
            'description', group['description']).strip()

        group = self.model('group').updateGroup(group)
        return self.model('group').filter(group, user)
    updateGroup.description = (
        Description('Update a group by ID.')
        .param('id', 'The ID of the group.', paramType='path')
        .param('name', 'The name to set on the group.', required=False)
        .param('description', 'Description for the group.', required=False)
        .param('public', 'Whether the group should be publicly visible',
               dataType='boolean')
        .errorResponse()
        .errorResponse('Write access was denied for the group.', 403))

    @access.user
    @loadmodel(model='group', level=AccessType.READ)
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
        user = self.getCurrentUser()
        joinedGroup = self.model('group').joinGroup(group, user)
        return self.model('group').filter(joinedGroup, user, accessList=True,
                                          requests=True)
    joinGroup.description = (
        Description('Request to join a group, or accept an invitation to join.')
        .responseClass('Group')
        .param('id', 'The ID of the group.', paramType='path')
        .errorResponse('ID was invalid.')
        .errorResponse('You were not invited to this group, or do not have '
                       'read access to it.', 403))

    @access.public
    @loadmodel(model='group', level=AccessType.READ)
    def listMembers(self, group, params):
        """
        Paginated member list of group members.

        :returns: A page of User documents representing members of the group.
        """
        limit, offset, sort = self.getPagingParameters(params, 'lastName')

        return list(self.model('group').listMembers(
            group, offset=offset, limit=limit, sort=sort))
    listMembers.description = (
        Description('List members of a group.')
        .param('id', 'The ID of the group.', paramType='path')
        .param('limit', "Result set size limit (default=50).", required=False,
               dataType='int')
        .param('offset', "Offset into result set (default=0).", required=False,
               dataType='int')
        .param('sort', "Field to sort the member list by (default=lastName)",
               required=False)
        .param('sortdir', "1 for ascending, -1 for descending (default=1)",
               required=False, dataType='int')
        .errorResponse('ID was invalid.')
        .errorResponse('Read access was denied for the group.', 403))

    @access.user
    @loadmodel(model='group', level=AccessType.WRITE)
    def inviteToGroup(self, group, params):
        """Invite the user to join the group."""
        self.requireParams('userId', params)
        user = self.getCurrentUser()
        level = int(params.get('level', AccessType.READ))
        force = self.boolParam('force', params, default=False)

        userToInvite = self.model('user').load(
            id=params['userId'], user=user, level=AccessType.READ, exc=True)

        if force:
            self.requireAdmin(user)
            self.model('group').addUser(group, userToInvite, level=level)
        else:
            # Can only invite into access levels that you yourself have
            self.model('group').requireAccess(group, user, level)
            self.model('group').inviteUser(group, userToInvite, level)

            if not self.boolParam('quiet', params, default=False):
                html = mail_utils.renderTemplate('groupInvite.mako', {
                    'userToInvite': userToInvite,
                    'user': user,
                    'group': group
                })
                mail_utils.sendEmail(
                    to=userToInvite['email'], text=html,
                    subject="Girder: You've been invited to a group")

        return self.model('group').filter(group, user, accessList=True,
                                          requests=True)
    inviteToGroup.description = (
        Description("Invite a user to join a group, or accept a user's request "
                    " to join.")
        .responseClass('Group')
        .notes('The "force" option to this endpoint is only available to '
               'administrators and can be used to bypass the invitation process'
               ' and instead add the user directly to the group.')
        .param('id', 'The ID of the group.', paramType='path')
        .param('userId', 'The ID of the user to invite or accept.')
        .param('level', 'The access level the user will be given when they '
               'accept the invitation. Defaults to read access (0).',
               required=False, dataType='int')
        .param('quiet', 'If you do not want this action to send an email to '
               'the target user, set this to true.', dataType='boolean',
               required=False)
        .param('force', 'Add user directly rather than sending an invitation '
               '(admin-only option).', dataType='boolean', required=False)
        .errorResponse()
        .errorResponse('Write access was denied for the group.', 403))

    @access.user
    @loadmodel(model='group', level=AccessType.ADMIN)
    def promoteToModerator(self, group, params):
        return self._promote(group, params, AccessType.WRITE)
    promoteToModerator.description = (
        Description('Promote a member to be a moderator of the group.')
        .responseClass('Group')
        .param('id', 'The ID of the group.', paramType='path')
        .param('userId', 'The ID of the user to promote.')
        .errorResponse('ID was invalid.')
        .errorResponse("You don't have permission to promote users.", 403))

    @access.user
    @loadmodel(model='group', level=AccessType.ADMIN)
    def promoteToAdmin(self, group, params):
        return self._promote(group, params, AccessType.ADMIN)
    promoteToAdmin.description = (
        Description('Promote a member to be an administrator of the group.')
        .responseClass('Group')
        .param('id', 'The ID of the group.', paramType='path')
        .param('userId', 'The ID of the user to promote.')
        .errorResponse('ID was invalid.')
        .errorResponse("You don't have permission to promote users.", 403))

    def _promote(self, group, params, level):
        """
        Promote a user to moderator or administrator.
        :param group: The group to promote within.
        :param params: Request parameters.
        :param level: Either WRITE or ADMIN, for moderator or administrator.
        :type level: AccessType
        :returns: The updated group document.
        """
        self.requireParams('userId', params)
        user = self.getCurrentUser()

        userToPromote = self.model('user').load(
            id=params['userId'], user=user, level=AccessType.READ, exc=True)

        if not group['_id'] in userToPromote.get('groups', []):
            raise AccessException('That user is not a group member.')

        group = self.model('group').setUserAccess(
            group, userToPromote, level=level, save=True)
        return self.model('group').filter(group, user, accessList=True)

    @access.user
    @loadmodel(model='group', level=AccessType.ADMIN)
    def demote(self, group, params):
        """
        Demote a user down to a normal member.

        :returns: The updated group document.
        """
        self.requireParams('userId', params)
        user = self.getCurrentUser()

        userToDemote = self.model('user').load(
            id=params['userId'], user=user, level=AccessType.READ, exc=True)

        group = self.model('group').setUserAccess(
            group, userToDemote, level=AccessType.READ, save=True)
        return self.model('group').filter(group, user, accessList=True,
                                          requests=True)
    demote.description = (
        Description('Demote a user to a normal group member.')
        .responseClass('Group')
        .param('id', 'The ID of the group.', paramType='path')
        .param('userId', 'The ID of the user to demote.')
        .errorResponse()
        .errorResponse("You don't have permission to demote users.", 403))

    @access.user
    @loadmodel(model='group', level=AccessType.READ)
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

        groupSansUser = self.model('group').removeUser(group, userToRemove)
        return self.model('group').filter(groupSansUser, user, requests=True,
                                          accessList=True)
    removeFromGroup.description = (
        Description('Remove a user from a group, or uninvite them.')
        .responseClass('Group')
        .notes("""If the specified user is not yet a member of the group, this
               will delete any outstanding invitation or membership request for
               the user. Passing no userId parameter will assume that the
               current user is removing himself.""")
        .param('id', 'The ID of the group.', paramType='path')
        .param('userId', 'The ID of the user to remove. If not passed, will '
               'remove yourself from the group.', required=False)
        .errorResponse()
        .errorResponse("You don't have permission to remove that user.", 403))

    @access.user
    @loadmodel(model='group', level=AccessType.ADMIN)
    def deleteGroup(self, group, params):
        self.model('group').remove(group)
        return {'message': 'Deleted the group {}.'.format(group['name'])}
    deleteGroup.description = (
        Description('Delete a group by ID.')
        .param('id', 'The ID of the group.', paramType='path')
        .errorResponse('ID was invalid.')
        .errorResponse('Admin access was denied for the group.', 403))
