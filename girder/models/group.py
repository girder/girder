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

from .model_base import AccessControlledModel,\
    ValidationException,\
    AccessException
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
        duplicates = self.find(q, limit=1, fields=['_id'])
        if duplicates.count() != 0:
            raise ValidationException('A group with that name already'
                                      'exists.', 'name')

        return doc

    def list(self, user=None, limit=50, offset=0, sort=None):
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
        cursor = self.find({}, limit=0, sort=sort)

        for r in self.filterResultsByPermission(cursor=cursor, user=user,
                                                level=AccessType.READ,
                                                limit=limit, offset=offset):
            yield r

    def listMembers(self, group, offset=0, limit=50, sort=None):
        """
        List members of the group, with names, ids, and logins.
        """
        fields = ['_id', 'firstName', 'lastName', 'login']
        return self.model('user').find({
            'groups': group['_id']
        }, fields=fields, limit=limit, offset=offset, sort=sort)

    def remove(self, group):
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

    def getMembers(self, group, offset=0, limit=50, sort=None):
        """
        Return the list of all users who belong to this group.

        :param group: The group to list members on.
        :param offset: Offset into the result set of users.
        :param limit: Result set size limit.
        :param sort: Sort parameter for the find query.
        :returns: List of user documents.
        """
        q = {
            'groups': group['_id']
        }
        cursor = self.model('user').find(
            q, offset=offset, limit=limit, sort=sort)
        users = []
        for user in cursor:
            users.append(user)

        return users

    def addUser(self, group, user, level=AccessType.READ):
        """
        Add the user to the group. Records membership in the group in the
        user document, and also grants the specified access level on the
        group itself to the user. Any group member has at least read access on
        the group. If the user already belongs to the group, this method can
        be used to change their access level within it.
        """
        if not 'groups' in user:
            user['groups'] = []

        if not group['_id'] in user['groups']:
            user['groups'].append(group['_id'])
            self.model('user').save(user, validate=False)

        self.setUserAccess(group, user, level, save=True)

        return group

    def joinGroup(self, group, user):
        """
        Call this when the user accepts an invitation.
        """
        if not 'groupInvites' in user:
            user['groupInvites'] = []

        for invite in user['groupInvites']:
            if invite['groupId'] == group['_id']:
                self.addUser(group, user, level=invite['level'])
                user['groupInvites'].remove(invite)
                self.model('user').save(user, validate=False)
                break
        else:
            raise AccessException('User was not invited to this group.')

        return group

    def inviteUser(self, group, user, level=AccessType.READ):
        """
        Invite a user to join the group. Inviting them automatically
        grants the user read access to the group so that they can see it.
        Once they accept the invitation, they will be given the specified level
        of access.
        """
        if group['_id'] in user.get('groups', []):
            raise ValidationException('User is already in this group.')

        if not 'groupInvites' in user:
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

    def removeUser(self, group, user):
        """
        Remove the user from the group. If the user is not in the group but
        has an outstanding invitation to the group, the invitation will be
        revoked.
        """
        # Remove group membership for this user.
        if 'groups' in user and group['_id'] in user['groups']:
            user['groups'].remove(group['_id'])

        # Remove any outstanding invitations for this group
        l = lambda inv: not inv['groupId'] == group['_id']
        user['groupInvites'] = filter(l, user.get('groupInvites', []))
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

        now = datetime.datetime.now()

        group = {
            'name': name,
            'description': description,
            'created': now,
            'updated': now
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
        group['updated'] = datetime.datetime.now()

        # Validate and save the group
        return self.save(group)

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

    def getFullAccessList(self, doc):
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
            AccessControlledModel.setUserAccess(
                self, doc, user, level, save=True)
        else:
            AccessControlledModel.setUserAccess(
                self, doc, user, level=None, save=True)
