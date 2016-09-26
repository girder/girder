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

from ..describe import Description, describeRoute
from ..rest import Resource, filtermodel, loadmodel
from girder.models.model_base import AccessException
from girder.constants import AccessType, SettingKey
from girder.utility import mail_utils
from girder.api import access


class Group(Resource):
    """API Endpoint for groups."""
    def __init__(self):
        super(Group, self).__init__()
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
    @filtermodel(model='group')
    @describeRoute(
        Description('Search for groups or list all groups.')
        .param('text', "Pass this to perform a full-text search for groups.",
               required=False)
        .pagingParams(defaultSort='name')
        .param('exact', 'If true, only return exact name matches. This is '
               'case sensitive.', required=False, dataType='boolean',
               default=False)
        .errorResponse()
    )
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
        return list(groupList)

    @access.user
    @filtermodel(model='group')
    @describeRoute(
        Description('Create a new group.')
        .responseClass('Group')
        .notes('Must be logged in.')
        .param('name', 'Unique name for the group.')
        .param('description', 'Description of the group.', required=False)
        .param('public', 'Whether the group should be publicly visible.',
               required=False, dataType='boolean', default=False)
        .errorResponse()
        .errorResponse('Write access was denied on the parent', 403)
    )
    def createGroup(self, params):
        self.requireParams('name', params)

        name = params['name'].strip()
        description = params.get('description', '').strip()
        public = self.boolParam('public', params, default=False)

        return self.model('group').createGroup(
            name=name, creator=self.getCurrentUser(), description=description,
            public=public)

    @access.public
    @loadmodel(model='group', level=AccessType.READ)
    @filtermodel(model='group')
    @describeRoute(
        Description('Get a group by ID.')
        .responseClass('Group')
        .param('id', 'The ID of the group.', paramType='path')
        .errorResponse('ID was invalid.')
        .errorResponse('Read access was denied for the group.', 403)
    )
    def getGroup(self, group, params):
        # Add in the current setting for adding to groups
        group['_addToGroupPolicy'] = self.model('setting').get(
            SettingKey.ADD_TO_GROUP_POLICY)
        return group

    @access.public
    @loadmodel(model='group', level=AccessType.READ)
    @filtermodel(model='group', addFields={'access', 'requests'})
    @describeRoute(
        Description('Get the access control list for a group.')
        .responseClass('Group')
        .param('id', 'The ID of the group.', paramType='path')
        .errorResponse('ID was invalid.')
        .errorResponse('Read access was denied for the group.', 403)
    )
    def getGroupAccess(self, group, params):
        groupModel = self.model('group')
        group['access'] = groupModel.getFullAccessList(group)
        group['requests'] = list(groupModel.getFullRequestList(group))
        return group

    @access.public
    @loadmodel(model='group', level=AccessType.READ)
    @filtermodel(model='user')
    @describeRoute(
        Description('Show outstanding invitations for a group.')
        .responseClass('Group')
        .param('id', 'The ID of the group.', paramType='path')
        .pagingParams(defaultSort='lastName')
        .errorResponse()
        .errorResponse('Read access was denied for the group.', 403)
    )
    def getGroupInvitations(self, group, params):
        limit, offset, sort = self.getPagingParameters(params, 'lastName')
        return list(self.model('group').getInvites(group, limit, offset, sort))

    @access.user
    @loadmodel(model='group', level=AccessType.WRITE)
    @filtermodel(model='group')
    @describeRoute(
        Description('Update a group by ID.')
        .param('id', 'The ID of the group.', paramType='path')
        .param('name', 'The name to set on the group.', required=False)
        .param('description', 'Description for the group.', required=False)
        .param('public', 'Whether the group should be publicly visible',
               dataType='boolean')
        .param('addAllowed', 'Can admins or moderators directly add members '
               'to this group?  Only system administrators are allowed to '
               'set this field', required=False,
               enum=['default', 'no', 'yesmod', 'yesadmin'])
        .errorResponse()
        .errorResponse('Write access was denied for the group.', 403)
    )
    def updateGroup(self, group, params):
        if 'public' in params:
            public = self.boolParam('public', params, default=False)
            self.model('group').setPublic(group, public)

        group['name'] = params.get('name', group['name']).strip()
        group['description'] = params.get(
            'description', group['description']).strip()
        if 'addAllowed' in params:
            self.requireAdmin(self.getCurrentUser())
            group['addAllowed'] = params.get('addAllowed')

        return self.model('group').updateGroup(group)

    @access.user
    @loadmodel(model='group', level=AccessType.READ)
    @filtermodel(model='group', addFields={'access', 'requests'})
    @describeRoute(
        Description('Request to join a group, or accept an invitation to join.')
        .responseClass('Group')
        .param('id', 'The ID of the group.', paramType='path')
        .errorResponse('ID was invalid.')
        .errorResponse('You were not invited to this group, or do not have '
                       'read access to it.', 403)
    )
    def joinGroup(self, group, params):
        groupModel = self.model('group')
        group = groupModel.joinGroup(group, self.getCurrentUser())
        group['access'] = groupModel.getFullAccessList(group)
        group['requests'] = list(groupModel.getFullRequestList(group))
        return group

    @access.public
    @loadmodel(model='group', level=AccessType.READ)
    @filtermodel(model='user')
    @describeRoute(
        Description('List members of a group.')
        .param('id', 'The ID of the group.', paramType='path')
        .pagingParams(defaultSort='lastName')
        .errorResponse('ID was invalid.')
        .errorResponse('Read access was denied for the group.', 403)
    )
    def listMembers(self, group, params):
        limit, offset, sort = self.getPagingParameters(params, 'lastName')

        return list(self.model('group').listMembers(
            group, offset=offset, limit=limit, sort=sort))

    @access.user
    @loadmodel(model='group', level=AccessType.WRITE)
    @filtermodel(model='group', addFields={'access', 'requests'})
    @describeRoute(
        Description("Invite a user to join a group, or accept a user's request "
                    " to join.")
        .responseClass('Group')
        .notes('The "force" option to this endpoint is only available to '
               'administrators and can be used to bypass the invitation process'
               ' and instead add the user directly to the group.')
        .param('id', 'The ID of the group.', paramType='path')
        .param('userId', 'The ID of the user to invite or accept.')
        .param('level', 'The access level the user will be given when they '
               'accept the invitation.',
               required=False, dataType='int', default=AccessType.READ)
        .param('quiet', 'If you do not want this action to send an email to '
               'the target user, set this to true.', dataType='boolean',
               required=False)
        .param('force', 'Add user directly rather than sending an invitation '
               '(admin-only option).', dataType='boolean', required=False)
        .errorResponse()
        .errorResponse('Write access was denied for the group.', 403)
    )
    def inviteToGroup(self, group, params):
        self.requireParams('userId', params)
        user = self.getCurrentUser()
        level = int(params.get('level', AccessType.READ))
        force = self.boolParam('force', params, default=False)
        groupModel = self.model('group')

        userToInvite = self.model('user').load(
            id=params['userId'], user=user, level=AccessType.READ, exc=True)

        if force:
            if not user['admin']:
                mustBeAdmin = True
                addPolicy = self.model('setting').get(
                    SettingKey.ADD_TO_GROUP_POLICY)
                addGroup = group.get('addAllowed', 'default')
                if addGroup not in ['no', 'yesadmin', 'yesmod']:
                    addGroup = addPolicy
                if (groupModel.hasAccess(
                        group, user, AccessType.ADMIN) and
                        ('mod' in addPolicy or 'admin' in addPolicy) and
                        addGroup.startswith('yes')):
                    mustBeAdmin = False
                elif (groupModel.hasAccess(
                        group, user, AccessType.WRITE) and
                        'mod' in addPolicy and
                        addGroup == 'yesmod'):
                    mustBeAdmin = False
                if mustBeAdmin:
                    self.requireAdmin(user)
            groupModel.addUser(group, userToInvite, level=level)
        else:
            # Can only invite into access levels that you yourself have
            groupModel.requireAccess(group, user, level)
            groupModel.inviteUser(group, userToInvite, level)

            if not self.boolParam('quiet', params, default=False):
                html = mail_utils.renderTemplate('groupInvite.mako', {
                    'userToInvite': userToInvite,
                    'user': user,
                    'group': group
                })
                mail_utils.sendEmail(
                    to=userToInvite['email'], text=html,
                    subject="Girder: You've been invited to a group")

        group['access'] = groupModel.getFullAccessList(group)
        group['requests'] = list(groupModel.getFullRequestList(group))
        return group

    @access.user
    @loadmodel(model='group', level=AccessType.ADMIN)
    @filtermodel(model='group', addFields={'access'})
    @describeRoute(
        Description('Promote a member to be a moderator of the group.')
        .responseClass('Group')
        .param('id', 'The ID of the group.', paramType='path')
        .param('userId', 'The ID of the user to promote.')
        .errorResponse('ID was invalid.')
        .errorResponse("You don't have permission to promote users.", 403)
    )
    def promoteToModerator(self, group, params):
        return self._promote(group, params, AccessType.WRITE)

    @access.user
    @loadmodel(model='group', level=AccessType.ADMIN)
    @filtermodel(model='group', addFields={'access'})
    @describeRoute(
        Description('Promote a member to be an administrator of the group.')
        .responseClass('Group')
        .param('id', 'The ID of the group.', paramType='path')
        .param('userId', 'The ID of the user to promote.')
        .errorResponse('ID was invalid.')
        .errorResponse("You don't have permission to promote users.", 403)
    )
    def promoteToAdmin(self, group, params):
        return self._promote(group, params, AccessType.ADMIN)

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
        group['access'] = self.model('group').getFullAccessList(group)
        return group

    @access.user
    @loadmodel(model='group', level=AccessType.ADMIN)
    @filtermodel(model='group', addFields={'access', 'requests'})
    @describeRoute(
        Description('Demote a user to a normal group member.')
        .responseClass('Group')
        .param('id', 'The ID of the group.', paramType='path')
        .param('userId', 'The ID of the user to demote.')
        .errorResponse()
        .errorResponse("You don't have permission to demote users.", 403)
    )
    def demote(self, group, params):
        self.requireParams('userId', params)
        user = self.getCurrentUser()

        userToDemote = self.model('user').load(
            id=params['userId'], user=user, level=AccessType.READ, exc=True)

        groupModel = self.model('group')
        group = groupModel.setUserAccess(
            group, userToDemote, level=AccessType.READ, save=True)
        group['access'] = groupModel.getFullAccessList(group)
        group['requests'] = list(groupModel.getFullRequestList(group))
        return group

    @access.user
    @loadmodel(model='group', level=AccessType.READ)
    @filtermodel(model='group', addFields={'access', 'requests'})
    @describeRoute(
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
        .errorResponse("You don't have permission to remove that user.", 403)
    )
    def removeFromGroup(self, group, params):
        user = self.getCurrentUser()
        groupModel = self.model('group')

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
            if groupModel.hasAccess(group, userToRemove, AccessType.ADMIN):
                groupModel.requireAccess(group, user, AccessType.ADMIN)
            else:
                groupModel.requireAccess(group, user, AccessType.WRITE)

        group = groupModel.removeUser(group, userToRemove)
        group['access'] = groupModel.getFullAccessList(group)
        group['requests'] = list(groupModel.getFullRequestList(group))
        return group

    @access.user
    @loadmodel(model='group', level=AccessType.ADMIN)
    @describeRoute(
        Description('Delete a group by ID.')
        .param('id', 'The ID of the group.', paramType='path')
        .errorResponse('ID was invalid.')
        .errorResponse('Admin access was denied for the group.', 403)
    )
    def deleteGroup(self, group, params):
        self.model('group').remove(group)
        return {'message': 'Deleted the group %s.' % group['name']}
