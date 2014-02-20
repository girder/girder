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

from .docs import group_docs
from ..rest import Resource, RestException
from ...models.model_base import ValidationException, AccessException
from ...constants import AccessType


class Group(Resource):
    """API Endpoint for groups."""

    def _filter(self, group, user, accessList=False, requests=False):
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

        return [self._filter(group, user) for group in self.model('group').list(
            user=user, offset=offset, limit=limit, sort=sort)]

    def createGroup(self, params):
        """
        Create a new group.

        :param params: Request query parameters.
        :type params: dict
        :returns: The created group document.
        """
        self.requireParams(['name'], params)

        name = params['name'].strip()
        description = params.get('description', '').strip()
        public = params.get('public', '').lower() == 'true'

        user = self.getCurrentUser()

        if user is None:
            raise AccessException('Must be logged in to create a group.')

        group = self.model('group').createGroup(
            name=name, creator=user, description=description, public=public)

        return self._filter(group, user)

    def updateGroup(self, id, user, params):
        """
        Update a group.

        :param id: The id of the group to update.
        :type id: str
        :param user: The current user.
        :type user: dict
        :param params: Request query parameters.
        :type params: dict
        :returns: The updated group document.
        """
        group = self.getObjectById(
            self.model('group'), id=id, user=user, checkAccess=True,
            level=AccessType.WRITE)

        public = params.get('public', 'false').lower() == 'true'
        self.model('group').setPublic(group, public)

        group['name'] = params.get('name', group['name']).strip()
        group['description'] = params.get(
            'description', group['description']).strip()

        group = self.model('group').updateGroup(group)
        return self._filter(group, user)

    def joinGroup(self, group, user):
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
            self.model('group').joinGroup(group, user), user,
            accessList=True, requests=True)

    def listMembers(self, group, params):
        """
        Paginated member list of group members.

        :param group: The group whose members to list.
        :type group: dict
        :param params: Request query parameters.
        :type params: dict
        :returns: A page of User documents representing members of the group.
        """
        limit, offset, sort = self.getPagingParameters(params, 'lastName')

        return [g for g in self.model('group').listMembers(
            group, offset=offset, limit=limit, sort=sort)]

    def inviteToGroup(self, group, user, params):
        """
        Invite the user to join the group.

        :param group: The group to invite the user to.
        :type group: dict
        :param user: The user doing the invitation.
        :type user: dict
        :param params: Optionally Pass a 'level' param with an
                       AccessType value (0-2) to grant the user that
                       access level when they join. Also must pass a
                       'userId' param, which is the ID of the user to
                       invite.
        :type params: dict
        :returns: The updated group document.
        """
        self.requireParams(['userId'], params)

        level = int(params.get('level', AccessType.READ))

        userToInvite = self.getObjectById(
            self.model('user'), user=user, id=params['userId'],
            checkAccess=True)

        # Can only invite into access levels that you yourself have
        self.model('group').requireAccess(group, user, level)
        self.model('group').inviteUser(group, userToInvite, level)

        return self._filter(group, user, accessList=True, requests=True)

    def promote(self, group, user, params, level):
        """
        Promote a user to moderator or administrator.
        :param group: The group to promote within.
        :param user: The current user.
        :param params: Request parameters.
        :param level: Either WRITE or ADMIN, for moderator or administrator.
        :type level: AccessType
        :returns: The updated group document.
        """
        self.requireParams(['userId'], params)

        userToPromote = self.getObjectById(
            self.model('user'), user=user, id=params['userId'],
            checkAccess=True)

        if not group['_id'] in userToPromote.get('groups', []):
            raise AccessException('That user is not a group member.')

        group = self.model('group').setUserAccess(
            group, userToPromote, level=level, save=True)
        return self._filter(group, user, accessList=True)

    def demote(self, group, user, params):
        """
        Demote a user down to a normal member.

        :param group: The group in which to demote this user.
        :type group: dict
        :param user: The current user (not the user being demoted).
        :type user: dict
        :param params: Request query parameters.
        :type params: dict
        :returns: The updated group document.
        """
        self.requireParams(['userId'], params)

        userToDemote = self.getObjectById(
            self.model('user'), user=user, id=params['userId'],
            checkAccess=True)
        group = self.model('group').setUserAccess(
            group, userToDemote, level=AccessType.READ, save=True)
        return self._filter(group, user, accessList=True, requests=True)

    def removeFromGroup(self, group, user, params):
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
        if 'userId' in params:
            userToRemove = self.getObjectById(
                self.model('user'), user=user, id=params['userId'],
                checkAccess=True)
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
            self.model('group').removeUser(group, userToRemove), user,
            accessList=True, requests=True)

    @Resource.endpoint
    def DELETE(self, path, params):
        if not path:
            raise RestException(
                'Path parameter should be the group ID to delete.')

        user = self.getCurrentUser()

        if len(path) == 1:
            group = self.getObjectById(
                self.model('group'), id=path[0], user=user, checkAccess=True,
                level=AccessType.ADMIN)
            self.model('group').remove(group)
            return {'message': 'Deleted the %s group.' % group['name']}
        elif path[1] == 'member':
            group = self.getObjectById(
                self.model('group'), id=path[0], user=user, checkAccess=True,
                level=AccessType.READ)
            return self.removeFromGroup(group, user, params)
        elif path[1] in ('admin', 'moderator'):
            group = self.getObjectById(
                self.model('group'), id=path[0], user=user, checkAccess=True,
                level=AccessType.ADMIN)
            return self.demote(group, user, params)
        else:
            raise RestException('Invalid group DELETE action.')

    @Resource.endpoint
    def GET(self, path, params):
        if not path:
            return self.find(params)

        user = self.getCurrentUser()
        group = self.getObjectById(
            self.model('group'), id=path[0], checkAccess=True, user=user)

        if len(path) == 1:
            return self._filter(group, user)
        elif path[1] == 'access':
            return self._filter(group, user, accessList=True, requests=True)
        elif path[1] == 'invitation':
            limit, offset, sort = self.getPagingParameters(params, 'lastName')
            return self.model('group').getInvites(group, limit, offset, sort)
        elif path[1] == 'member':
            return self.listMembers(group, params)
        else:
            raise RestException('Invalid group GET action.')

    @Resource.endpoint
    def POST(self, path, params):
        if not path:
            return self.createGroup(params)

        user = self.getCurrentUser()

        if len(path) == 2 and path[1] == 'invitation':
            group = self.getObjectById(
                self.model('group'), id=path[0], user=user,
                checkAccess=True, level=AccessType.WRITE)
            return self.inviteToGroup(group, user, params)
        elif len(path) == 2 and path[1] == 'member':
            group = self.getObjectById(
                self.model('group'), id=path[0], user=user,
                checkAccess=True, level=AccessType.READ)
            return self.joinGroup(group, user)
        elif len(path) == 2 and path[1] == 'moderator':
            group = self.getObjectById(
                self.model('group'), id=path[0], user=user,
                checkAccess=True, level=AccessType.ADMIN)
            return self.promote(group, user, params, AccessType.WRITE)
        elif len(path) == 2 and path[1] == 'admin':
            group = self.getObjectById(
                self.model('group'), id=path[0], user=user,
                checkAccess=True, level=AccessType.ADMIN)
            return self.promote(group, user, params, AccessType.ADMIN)
        else:
            raise RestException('Invalid path for group POST.')

    @Resource.endpoint
    def PUT(self, path, params):
        if not path:
            raise RestException('Must have a path parameter.')

        user = self.getCurrentUser()

        if len(path) == 1:
            return self.updateGroup(path[0], user, params)
        else:
            raise RestException('Invalid group update action.')
