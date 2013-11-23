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
    typically only performed ona single group at a time, so doing a find on the
    indexed group list in the user collection is sufficiently fast.

    Users with READ access on the group can see the group and its members.
    Users with WRITE access on the group can add and remove members and
    change the name or description.
    Users with ADMIN access can delete the entire group.
    """

    def initialize(self):
        self.name = 'group'
        self.ensureIndices(['lowerName'])

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

    def search(self, text=None, user=None, limit=50, offset=0, sort=None):
        """
        Search for groups or simply list all visible groups.

        :param text: Pass this to perform a text search of all groups.
        :param user: The user to search as.
        :param limit: Result set size limit.
        :param offset: Offset into the results.
        :param sort: The sort direction.
        """
        if text:
            # TODO text search
            return []
        else:
            # Perform the find; we'll do access-based filtering of the result
            # set afterward.
            cursor = self.find({}, limit=0, sort=sort)

            return self.filterResultsByPermission(cursor=cursor, user=user,
                                                  level=AccessType.READ,
                                                  limit=limit, offset=offset)

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
        the group.
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
        # User has to be able to see the group to join it
        self.setUserAccess(group, user, AccessType.READ, save=True)

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
        Remove the user from the group.
        """
        # Remove group membership for this user.
        if 'groups' in user and group['_id'] in user['groups']:
            user['groups'].remove(group['_id'])
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
