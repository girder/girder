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

from .. import base
from girder.constants import AccessType


def setUpModule():
    base.startServer()


def tearDownModule():
    base.stopServer()


class GroupTestCase(base.TestCase):
    def setUp(self):
        base.TestCase.setUp(self)

        # Create a set of users so we can work with these groups
        self.users = [self.model('user').createUser(
            'usr%s' % num, 'passwd', 'tst', 'usr', 'u%s@u.com' % num)
            for num in [0, 1, 2]]

    def testDeleteGroupDeletesAccessReferences(self):
        """
        This test ensures that when a group is deleted, references to it in
        various access-control lists are also removed.
        """
        # Create a couple of groups
        group1 = self.model('group').createGroup('g1', self.users[0])
        group2 = self.model('group').createGroup('g2', self.users[0])

        # Create a folder and give both groups some access on it
        folder = self.model('folder').createFolder(
            parent=self.users[0], name='x', parentType='user', public=False,
            creator=self.users[0])
        self.model('folder').setGroupAccess(folder, group1, AccessType.WRITE)
        self.model('folder').setGroupAccess(folder, group2, AccessType.READ)
        folder = self.model('folder').save(folder)

        self.assertEqual(len(folder['access']['groups']), 2)

        # Delete group 1; folder access list should no longer contain it
        self.model('group').remove(group1)
        group1 = self.model('group').load(group1['_id'])
        folder = self.model('folder').load(folder['_id'], force=True)

        self.assertEqual(group1, None)
        self.assertEqual(len(folder['access']['groups']), 1)

    def testGetGroups(self):
        """
        Test the GET endpoints for groups, including getting a single
        group and getting the list of all groups.
        """
        privateGroup = self.model('group').createGroup(
            'private ', self.users[0], public=False)
        publicGroup = self.model('group').createGroup(
            'public ', self.users[0], public=True)

        # Error: Invalid GET URL
        resp = self.request(path='/group/{}/foo'.format(publicGroup['_id']),
                            method='GET')
        self.assertStatus(resp, 400)

        # Anonymous user should be able to see the public group
        resp = self.request(
            path='/group/%s' % publicGroup['_id'], method='GET')
        self.assertStatusOk(resp)
        self.assertEqual(resp.json['name'], 'public')

        # Anonymous user should not be able to see the private group
        resp = self.request(
            path='/group/%s' % privateGroup['_id'], method='GET')
        self.assertStatus(resp, 401)

        # User 0 should be able to see the private group
        resp = self.request(
            path='/group/%s' % privateGroup['_id'], method='GET',
            user=self.users[0])
        self.assertStatusOk(resp)
        self.assertEqual(resp.json['name'], 'private')

        # Test listing all groups
        resp = self.request(path='/group/', method='GET', user=self.users[0])
        self.assertStatusOk(resp)
        self.assertEqual(type(resp.json), list)
        self.assertEqual(len(resp.json), 2)

        resp = self.request(path='/group/', method='GET', user=self.users[1])
        self.assertStatusOk(resp)
        self.assertEqual(type(resp.json), list)
        self.assertEqual(len(resp.json), 1)
        self.assertEqual(resp.json[0]['_id'], str(publicGroup['_id']))

    def testUpdateGroup(self):
        """
        Test editing the properties of a group.
        """
        group = self.model('group').createGroup(
            'public ', self.users[0], public=True)

        # Error: no ID parameter
        resp = self.request(path='/group/', method='PUT', user=self.users[0])
        self.assertStatus(resp, 400)

        # Error: too many parameters
        resp = self.request(path='/group/foo/bar', method='PUT',
                            user=self.users[0])
        self.assertStatus(resp, 400)

        params = {
            'public': 'false',
            'name': 'new name ',
            'description': ' a description. '
        }

        resp = self.request(path='/group/{}'.format(group['_id']),
                            method='PUT', user=self.users[0], params=params)
        self.assertStatusOk(resp)

        group = self.model('group').load(group['_id'], force=True)
        self.assertEqual(group['public'], False)
        self.assertEqual(group['name'], params['name'].strip())
        self.assertEqual(group['description'], params['description'].strip())

    def testGroupAccess(self):
        """
        Test creation, invitation, joining, and removing of users from
        groups.
        """
        self.ensureRequiredParams(
            path='/group', method='POST', required=['name'])

        params = {
            'name': ' A group name ',
            'description': 'my description ',
            'public': 'true'
        }

        # Anonymous users can't make groups
        resp = self.request(path='/group', method='POST', params=params)
        self.assertStatus(resp, 401)
        self.assertEqual('Must be logged in to create a group.',
                         resp.json['message'])

        # Have user 0 make a public group
        resp = self.request(path='/group', method='POST', params=params,
                            user=self.users[0])
        self.assertStatusOk(resp)
        self.assertEqual(resp.json['name'], params['name'].strip())
        self.assertEqual(resp.json['description'],
                         params['description'].strip())

        publicGroup = self.model('group').load(resp.json['_id'], force=True)

        # User 1 should be able to see the public group
        self.assertTrue(self.model('group').hasAccess(
            publicGroup, self.users[0], AccessType.ADMIN))
        self.assertTrue(self.model('group').hasAccess(
            publicGroup, self.users[1], AccessType.READ))

        # Try to make group with same name; should fail
        resp = self.request(path='/group', method='POST', params=params,
                            user=self.users[0])
        self.assertValidationError(resp, 'name')

        # Make a private group now
        params['public'] = 'false'
        params['name'] = 'different name'
        resp = self.request(path='/group', method='POST', params=params,
                            user=self.users[0])
        self.assertStatusOk(resp)
        self.assertEqual(resp.json['name'], params['name'].strip())
        self.assertEqual(resp.json['description'],
                         params['description'].strip())
        privateGroup = self.model('group').load(resp.json['_id'], force=True)

        # User 1 should not be able to see it
        self.assertTrue(self.model('group').hasAccess(
            privateGroup, self.users[0], AccessType.ADMIN))
        self.assertFalse(self.model('group').hasAccess(
            privateGroup, self.users[1], AccessType.READ))

        self.assertEqual(len(self.model('group').getMembers(privateGroup)), 1)

        # Invite user 1 to join the private group as member
        self.assertTrue(base.mockSmtp.isMailQueueEmpty())
        params = {
            'userId': self.users[1]['_id'],
            'level': AccessType.READ
        }
        resp = self.request(
            path='/group/%s/invitation' % privateGroup['_id'],
            user=self.users[0], method='POST', params=params)
        self.assertStatusOk(resp)

        # We should see the invitation in the list
        resp = self.request(
            path='/group/{}/invitation'.format(privateGroup['_id']),
            user=self.users[0], method='GET')
        self.assertStatusOk(resp)
        self.assertEqual(len(resp.json), 1)
        self.assertEqual(resp.json[0]['_id'], str(self.users[1]['_id']))

        # An email should have been sent
        self.assertTrue(base.mockSmtp.waitForMail())

        # Reload user and group since they've changed in the database
        self.users[1] = self.model('user').load(
            self.users[1]['_id'], force=True)
        privateGroup = self.model('group').load(privateGroup['_id'], force=True)

        # User object should now have an invitation set on it
        self.assertTrue(privateGroup['_id'] in [
            invite['groupId'] for invite in self.users[1]['groupInvites']])

        # User 1 should now be able to see the group, but should not be in it.
        self.assertTrue(self.model('group').hasAccess(
            privateGroup, self.users[1], AccessType.READ))
        self.assertEqual(len(self.model('group').getMembers(privateGroup)), 1)

        # Removing user 1 from the group before they join it should remove the
        # invitation.
        resp = self.request(
            path='/group/%s/member' % privateGroup['_id'], user=self.users[0],
            method='DELETE', params={'userId': self.users[1]['_id']})
        self.assertStatusOk(resp)
        self.users[1] = self.model('user').load(
            self.users[1]['_id'], force=True)
        self.assertEqual(0, len(self.users[1]['groupInvites']))

        # Now re-invite user 1
        resp = self.request(
            path='/group/%s/invitation' % privateGroup['_id'],
            user=self.users[0], method='POST', params=params)
        self.assertStatusOk(resp)

        # User 1 should not yet be in the member list
        resp = self.request(
            path='/group/{}/member'.format(privateGroup['_id']),
            user=self.users[0], method='GET')
        self.assertStatusOk(resp)
        self.assertEqual(len(resp.json), 1)
        self.assertEqual(resp.json[0]['_id'], str(self.users[0]['_id']))

        # Have user 1 join the group
        resp = self.request(
            path='/group/%s/member' % privateGroup['_id'], method='POST',
            user=self.users[1])
        self.assertStatusOk(resp)

        # User 1 should now be in the member list
        resp = self.request(
            path='/group/{}/member'.format(privateGroup['_id']),
            user=self.users[0], method='GET')
        self.assertStatusOk(resp)
        self.assertEqual(len(resp.json), 2)
        self.assertEqual(resp.json[1]['_id'], str(self.users[1]['_id']))

        # Reload user and group since they've changed in the database
        self.users[1] = self.model('user').load(
            self.users[1]['_id'], force=True)
        privateGroup = self.model('group').load(privateGroup['_id'], force=True)

        # Invitation should be gone from user 1
        self.assertFalse(privateGroup['_id'] in [
            invite['groupId'] for invite in self.users[1]['groupInvites']])

        # User 1 should not be able to invite other members
        params = {
            'userId': self.users[2]['_id'],
            'level': AccessType.READ
        }
        resp = self.request(
            path='/group/%s/invitation' % privateGroup['_id'],
            user=self.users[1], method='POST', params=params)
        self.assertStatus(resp, 403)

        # We promote user 1 to moderator
        resp = self.request(
            path='/group/{}/moderator'.format(privateGroup['_id']),
            user=self.users[0], method='POST', params={
                'userId': self.users[1]['_id']
            })
        self.assertStatusOk(resp)

        # User 1 should not be able to invite anyone as admin
        params['level'] = AccessType.ADMIN
        resp = self.request(
            path='/group/%s/invitation' % privateGroup['_id'],
            user=self.users[1], method='POST', params=params)
        self.assertStatus(resp, 403)

        # User 1 should be able to invite someone with write access
        params['level'] = AccessType.WRITE
        resp = self.request(
            path='/group/{}/invitation'.format(privateGroup['_id']),
            user=self.users[1], method='POST', params=params)
        self.assertStatusOk(resp)

        # Have user 2 join the group
        resp = self.request(
            path='/group/{}/member'.format(privateGroup['_id']), method='POST',
            user=self.users[2])
        self.assertStatusOk(resp)

        # User 1 should not be able to remove a group admin
        params['userId'] = self.users[0]['_id']
        resp = self.request(
            path='/group/%s/member' % privateGroup['_id'], user=self.users[1],
            method='DELETE', params=params)
        self.assertStatus(resp, 403)
        self.assertEqual(resp.json['message'], 'Admin access denied for group.')

        # User 1 should not be able to delete the group
        resp = self.request(
            path='/group/%s' % privateGroup['_id'], user=self.users[1],
            method='DELETE')
        self.assertStatus(resp, 403)
        self.assertEqual(resp.json['message'], 'Admin access denied for group.')

        # We promote user 1 to admin
        resp = self.request(
            path='/group/{}/admin'.format(privateGroup['_id']),
            user=self.users[0], method='POST', params={
                'userId': self.users[1]['_id']
            })
        self.assertStatusOk(resp)
        privateGroup = self.model('group').load(privateGroup['_id'], force=True)
        self.assertTrue(self.model('group').hasAccess(privateGroup,
                                                      self.users[1],
                                                      AccessType.ADMIN))

        # User 1 should now be able to promote and demote members
        resp = self.request(
            path='/group/{}/admin'.format(privateGroup['_id']),
            user=self.users[1], method='POST', params={
                'userId': self.users[2]['_id']
            })
        self.assertStatusOk(resp)
        privateGroup = self.model('group').load(privateGroup['_id'], force=True)
        self.assertTrue(self.model('group').hasAccess(privateGroup,
                                                      self.users[2],
                                                      AccessType.ADMIN))

        resp = self.request(
            path='/group/{}/admin'.format(privateGroup['_id']),
            user=self.users[1], method='DELETE', params={
                'userId': self.users[2]['_id']
            })
        self.assertStatusOk(resp)
        privateGroup = self.model('group').load(privateGroup['_id'], force=True)
        self.assertFalse(self.model('group').hasAccess(privateGroup,
                                                       self.users[2],
                                                       AccessType.ADMIN))

        # User 2 should be able to leave the group
        self.users[2] = self.model('user').load(
            self.users[2]['_id'], force=True)
        self.assertTrue(privateGroup['_id'] in self.users[2]['groups'])
        resp = self.request(
            path='/group/{}/member'.format(privateGroup['_id']),
            user=self.users[2], method='DELETE')
        self.assertStatusOk(resp)
        self.users[2] = self.model('user').load(
            self.users[2]['_id'], force=True)
        self.assertFalse(privateGroup['_id'] in self.users[2]['groups'])

        # User 0 should be able to remove user 1
        params['userId'] = self.users[1]['_id']
        self.assertEqual(len(self.model('group').getMembers(privateGroup)), 2)
        resp = self.request(
            path='/group/%s/member' % privateGroup['_id'], user=self.users[0],
            method='DELETE', params=params)
        self.assertStatusOk(resp)
        self.assertEqual(len(self.model('group').getMembers(privateGroup)), 1)

        # User 0 should be able to delete the group
        self.users[0] = self.model('user').load(
            self.users[0]['_id'], force=True)
        self.assertEqual(len(self.users[0]['groups']), 2)
        resp = self.request(
            path='/group/%s' % privateGroup['_id'], user=self.users[0],
            method='DELETE')
        self.assertStatusOk(resp)
        self.assertEqual(resp.json['message'], 'Deleted the group {}.'.format(
            privateGroup['name']))
        privateGroup = self.model('group').load(privateGroup['_id'], force=True)
        self.assertTrue(privateGroup is None)

        # Make sure group reference was removed from user 0
        self.users[0] = self.model('user').load(
            self.users[0]['_id'], force=True)
        self.assertEqual(len(self.users[0]['groups']), 1)
