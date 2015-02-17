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

import datetime

from .model_base import AccessControlledModel, ValidationException
from girder.constants import AccessType


class Group(AccessControlledModel):
    """
    Groups are simply groups of users. The primary use of grouping users is
    to simplify access control for resources in the system, but they can
    be used for other purposes that require groupings of users as well.

    Group membership is stored in the database on the user document only;
    there is no "users" field in this model. This is to optimize for the most
    common use case for querying membership, which involves checking access
    control policies, which is always done relative to a specific user. The
    task of querying all members within a group is much less common and
    typically only performed on a single group at a time, so doing a find on the
    indexed group list in the user collection is sufficiently fast.

    Users with READ access on the group can see the group and its members.
    Users with WRITE access on the group can add and remove members and
    change the name or description.
    Users with ADMIN access can promote group members to grant them WRITE or
    ADMIN access, and can also delete the entire group.

    This model uses a custom implementation of the access control methods,
    because it uses only a subset of its capabilities and provides a more
    optimized implementation for that subset. Specifically: read access is
    implied by membership in the group or having an invitation to join the
    group, so we don't store read access in the access document as normal.
    Another constraint is that write and admin access on the group can only be
    granted to members of the group. Also, group permissions are not allowed
    on groups for the sake of simplicity.
    """

    def initialize(self):
        self.name = 'group'
        self.ensureIndices(['lowerName'])
        self.ensureTextIndex({
            'name': 10,
            'description': 1
        })

        self.exposeFields(level=AccessType.READ, fields=(
            '_id', 'name', 'public', 'description', 'created', 'updated'))

    def filter(self, group, user, accessList=False, requests=False):
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
        filtered = AccessControlledModel.filter(self, doc=group, user=user)

        if accessList:
            filtered['access'] = self.getFullAccessList(group)

        if requests:
            filtered['requests'] = list(self.getFullRequestList(group))

        return filtered

    def validate(self, doc):
        doc['name'] = doc['name'].strip()
        doc['lowerName'] = doc['name'].lower()
        doc['description'] = doc['description'].strip()

        if not doc['name']:
            raise ValidationException('Group name must not be empty.', 'name')

        q = {
            'lowerName': doc['lowerName'],
        }
        if '_id' in doc:
            q['_id'] = {'$ne': doc['_id']}
        duplicate = self.findOne(q, fields=['_id'])
        if duplicate is not None:
            raise ValidationException('A group with that name already exists.',
                                      field='name')

        return doc

    def list(self, user=None, limit=0, offset=0, sort=None):
        """
        Search for groups or simply list all visible groups.

        :param text: Pass this to perform a text search of all groups.
        :param user: The user to search as.
        :param limit: Result set size limit.
        :param offset: Offset into the results.
        :param sort: The sort direction.
        """
        # Perform the find; we'll do access-based filtering of the result
        # set afterward.
        cursor = self.find({}, sort=sort)

        return self.filterResultsByPermission(
            cursor=cursor, user=user, level=AccessType.READ, limit=limit,
            offset=offset)

    def listMembers(self, group, offset=0, limit=0, sort=None):
        """
        List members of the group, with names, ids, and logins.
        """
        fields = ['_id', 'firstName', 'lastName', 'login']
        return self.model('user').find({
            'groups': group['_id']
        }, fields=fields, limit=limit, offset=offset, sort=sort)

    def remove(self, group, **kwargs):
        """
        Delete a group, and all references to it in the database.

        :param group: The group document to delete.
        :type group: dict
        """

        # Remove references to this group from user group membership lists
        self.model('user').update({
            'groups': group['_id']
        }, {
            '$pull': {'groups': group['_id']}
        })

        acQuery = {
            'access.groups.id': group['_id']
        }
        acUpdate = {
            '$pull': {
                'access.groups': {'id': group['_id']}
            }
        }

        # Remove references to this group from access-controlled collections.
        self.update(acQuery, acUpdate)
        self.model('collection').update(acQuery, acUpdate)
        self.model('folder').update(acQuery, acUpdate)
        self.model('user').update(acQuery, acUpdate)

        # Finally, delete the document itself
        AccessControlledModel.remove(self, group)

    def getMembers(self, group, offset=0, limit=0, sort=None):
        """
        Return the list of all users who belong to this group.

        :param group: The group to list members on.
        :param offset: Offset into the result set of users.
        :param limit: Result set size limit.
        :param sort: Sort parameter for the find query.
        :returns: List of user documents.
        """
        return self.model('user').find(
            {'groups': group['_id']},
            offset=offset, limit=limit, sort=sort)

    def addUser(self, group, user, level=AccessType.READ):
        """
        Add the user to the group. Records membership in the group in the
        user document, and also grants the specified access level on the
        group itself to the user. Any group member has at least read access on
        the group. If the user already belongs to the group, this method can
        be used to change their access level within it.
        """
        if 'groups' not in user:
            user['groups'] = []

        if not group['_id'] in user['groups']:
            user['groups'].append(group['_id'])
            self.model('user').save(user, validate=False)

        # Delete outstanding request if one exists
        self._deleteRequest(group, user)

        self.setUserAccess(group, user, level, save=True)

        return group

    def _deleteRequest(self, group, user):
        """
        Helper method to delete a request for the given user.
        """
        if user['_id'] in group.get('requests', []):
            group['requests'].remove(user['_id'])
            self.save(group, validate=False)

    def joinGroup(self, group, user):
        """
        This method either accepts an invitation to join a group, or if the
        given user has not been invited to the group, this will create an
        invitation request that moderators and admins may grant or deny later.
        """
        if 'groupInvites' not in user:
            user['groupInvites'] = []

        for invite in user['groupInvites']:
            if invite['groupId'] == group['_id']:
                self.addUser(group, user, level=invite['level'])
                user['groupInvites'].remove(invite)
                self.model('user').save(user, validate=False)
                break
        else:
            if 'requests' not in group:
                group['requests'] = []

            if not user['_id'] in group['requests']:
                group['requests'].append(user['_id'])
                self.save(group, validate=False)

        return group

    def inviteUser(self, group, user, level=AccessType.READ):
        """
        Invite a user to join the group. Inviting them automatically
        grants the user read access to the group so that they can see it.
        Once they accept the invitation, they will be given the specified level
        of access.

        If the user has requested an invitation to this group, calling this
        will accept their request and add them to the group at the access
        level specified.
        """
        if group['_id'] in user.get('groups', []):
            raise ValidationException('User is already in this group.')

        # If there is an outstanding request to join from this user, we
        # just add them to the group instead of invite them.
        if user['_id'] in group.get('requests', []):
            return self.addUser(group, user, level)

        if 'groupInvites' not in user:
            user['groupInvites'] = []

        for invite in user['groupInvites']:
            if invite['groupId'] == group['_id']:
                invite['level'] = level
                break
        else:
            user['groupInvites'].append({
                'groupId': group['_id'],
                'level': level
            })

        return self.model('user').save(user, validate=False)

    def getInvites(self, group, limit=0, offset=0, sort=None):
        """
        Return a page of outstanding invitations to a group. This is simply
        a list of users invited to the group currently.

        :param group: The group to find invitations for.
        :param limit: Result set size limit.
        :param offset: Offset into the results.
        :param sort: The sort field.
        """
        return self.model('user').find(
            {'groupInvites.groupId': group['_id']},
            limit=limit, offset=offset, sort=sort,
            fields=['_id', 'firstName', 'lastName', 'login'])

    def removeUser(self, group, user):
        """
        Remove the user from the group. If the user is not in the group but
        has an outstanding invitation to the group, the invitation will be
        revoked. If the user has requested an invitation, calling this will
        deny that request, thereby deleting it.
        """
        # Remove group membership for this user.
        if 'groups' in user and group['_id'] in user['groups']:
            user['groups'].remove(group['_id'])

        # Remove outstanding requests from this user
        self._deleteRequest(group, user)

        # Remove any outstanding invitations for this group
        user['groupInvites'] = filter(
            lambda inv: not inv['groupId'] == group['_id'],
            user.get('groupInvites', []))
        self.model('user').save(user, validate=False)

        # Remove all group access for this user on this group.
        self.setUserAccess(group, user, level=None, save=True)

        return group

    def createGroup(self, name, creator, description='', public=True):
        """
        Create a new group. The creator will be given admin access to it.

        :param name: The name of the folder.
        :type name: str
        :param description: Description for the folder.
        :type description: str
        :param public: Whether the group is publicly visible.
        :type public: bool
        :param creator: User document representing the creator of the group.
        :type creator: dict
        :returns: The group document that was created.
        """
        assert type(public) is bool

        now = datetime.datetime.utcnow()

        group = {
            'name': name,
            'description': description,
            'created': now,
            'updated': now,
            'requests': []
        }

        self.setPublic(group, public=public)

        # Now validate and save the group
        self.save(group)

        # We make the creator a member of this group and also grant them
        # admin access over the group.
        self.addUser(group, creator, level=AccessType.ADMIN)

        return group

    def updateGroup(self, group):
        """
        Updates a group.

        :param group: The group document to update
        :type group: dict
        :returns: The group document that was edited.
        """
        group['updated'] = datetime.datetime.utcnow()

        # Validate and save the group
        return self.save(group)

    def getFullRequestList(self, group):
        """
        Return the set of all outstanding requests, filled in with the login
        and full names of the corresponding users.

        :param group: The group to get requests for.
        :type group: dict
        """
        for userId in group.get('requests', []):
            user = self.model('user').load(
                userId, force=True, fields=['firstName', 'lastName', 'login'])
            yield {
                'id': userId,
                'login': user['login'],
                'name': '{} {}'.format(user['firstName'], user['lastName'])
            }

    def hasAccess(self, doc, user=None, level=AccessType.READ):
        """
        This overrides the default AccessControlledModel behavior for checking
        access to perform an optimized subset of the access control behavior.

        :param doc: The group to check permission on.
        :type doc: dict
        :param user: The user to check against.
        :type user: dict
        :param level: The access level.
        :type level: AccessType
        :returns: Whether the access is granted.
        """
        if user is None:
            # Short-circuit the case of anonymous users
            return level == AccessType.READ and doc.get('public', False) is True
        elif user.get('admin', False) is True:
            # Short-circuit the case of admins
            return True
        elif level == AccessType.READ:
            # For read access, just check user document for membership or public
            return doc.get('public', False) is True or\
                doc['_id'] in user.get('groups', []) or\
                doc['_id'] in [i['groupId'] for i in
                               user.get('groupInvites', [])]
        else:
            # Check the actual permissions document for >=WRITE access
            return self._hasUserAccess(doc.get('access', {}).get('users', []),
                                       user['_id'], level)

    def getAccessLevel(self, doc, user):
        """
        Return the maximum access level for a given user on the group.

        :param doc: The group to check access on.
        :param user: The user to get the access level for.
        :returns: The max AccessType available for the user on the object.
        """
        if user is None:
            if doc.get('public', False):
                return AccessType.READ
            else:
                return AccessType.NONE
        elif user.get('admin', False):
            return AccessType.ADMIN
        else:
            access = doc.get('access', {})
            level = AccessType.NONE

            if doc['_id'] in user.get('groups', []):
                level = AccessType.READ
            elif doc['_id'] in [i['groupId'] for i in
                                user.get('groupInvites', [])]:
                return AccessType.READ

            for userAccess in access.get('users', []):
                if userAccess['id'] == user['_id']:
                    level = max(level, userAccess['level'])
                    if level == AccessType.ADMIN:
                        return level

            return level

    def setAccessList(self, doc, access, save=False):
        raise Exception('Not implemented.')  # pragma: no cover

    def setGroupAccess(self, doc, group, level, save=False):
        raise Exception('Not implemented.')  # pragma: no cover

    def copyAccessPolicies(self, src, dest, save=False):
        raise Exception('Not implemented.')  # pragma: no cover

    def setUserAccess(self, doc, user, level, save=False):
        """
        This override is used because we only need to augment the access
        field in the case of WRITE access and above since READ access is
        implied by membership or invitation.
        """
        if level > AccessType.READ:
            doc = AccessControlledModel.setUserAccess(
                self, doc, user, level, save=True)
        else:
            doc = AccessControlledModel.setUserAccess(
                self, doc, user, level=None, save=True)

        return doc
