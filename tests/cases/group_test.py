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

import cherrypy
import json

from .. import base
from girder.constants import AccessType


def setUpModule():
    base.startServer()


def tearDownModule():
    base.stopServer()


class GroupTestCase(base.TestCase):
    def setUp(self):
        base.TestCase.setUp(self)

        self.requireModels(['user', 'group'])

        # Create a set of users so we can work with these groups
        self.users = [self.userModel.createUser(
            'usr%s' % num, 'passwd', 'tst', 'usr', 'u%s@u.com' % num)
            for num in [0, 1, 2]]

    def testGroupIndex(self):
        """
        Test the GET endpoints for groups, including getting a single
        group and getting the list of all groups.
        """
        pass  # TODO

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
        self.assertStatus(resp, 403)
        self.assertEqual('Must be logged in to create a group.',
                         resp.json['message'])

        # Have user 0 make a public group
        resp = self.request(path='/group', method='POST', params=params,
                            user=self.users[0])
        self.assertStatusOk(resp)
        self.assertEqual(resp.json['name'], params['name'].strip())
        self.assertEqual(resp.json['description'],
                         params['description'].strip())

        publicGroup = self.groupModel.load(resp.json['_id'], force=True)

        # User 1 should be able to see the public group
        self.assertTrue(self.groupModel.hasAccess(
            publicGroup, self.users[0], AccessType.ADMIN))
        self.assertTrue(self.groupModel.hasAccess(
            publicGroup, self.users[1], AccessType.READ))

        # User 1 should not be able to join the public group without invite.
        resp = self.request(
            path='/group/%s/join' % publicGroup['_id'], method='PUT',
            user=self.users[1])
        self.assertStatus(resp, 403)
        self.assertEqual(resp.json['message'],
                         'User was not invited to this group.')

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
        privateGroup = self.groupModel.load(resp.json['_id'], force=True)

        # User 1 should not be able to see it
        self.assertTrue(self.groupModel.hasAccess(
            privateGroup, self.users[0], AccessType.ADMIN))
        self.assertFalse(self.groupModel.hasAccess(
            privateGroup, self.users[1], AccessType.READ))

        self.assertEqual(len(self.groupModel.getMembers(privateGroup)), 1)

        # Invite user 1 to join the private group as member
        params = {
            'userId': self.users[1]['_id'],
            'level': AccessType.READ
        }
        resp = self.request(
            path='/group/%s/invite' % privateGroup['_id'], user=self.users[0],
            method='PUT', params=params)
        self.assertStatusOk(resp)

        # Reload user and group since they've changed in the database
        self.users[1] = self.userModel.load(self.users[1]['_id'], force=True)
        privateGroup = self.groupModel.load(privateGroup['_id'], force=True)

        # User object should now have an invitation set on it
        self.assertTrue(privateGroup['_id'] in [
            invite['groupId'] for invite in self.users[1]['groupInvites']])

        # User 1 should now be able to see the group, but should not be in it.
        self.assertTrue(self.groupModel.hasAccess(
            privateGroup, self.users[1], AccessType.READ))
        self.assertEqual(len(self.groupModel.getMembers(privateGroup)), 1)

        # Have user 1 join the group
        resp = self.request(
            path='/group/%s/join' % privateGroup['_id'], method='PUT',
            user=self.users[1])
        self.assertStatusOk(resp)

        # Reload user and group since they've changed in the database
        self.users[1] = self.userModel.load(self.users[1]['_id'], force=True)
        privateGroup = self.groupModel.load(privateGroup['_id'], force=True)

        # Invitation should be gone from user 1
        self.assertFalse(privateGroup['_id'] in [
            invite['groupId'] for invite in self.users[1]['groupInvites']])

        # User 1 should be a member of the group
        self.assertEqual(len(self.groupModel.getMembers(privateGroup)), 2)

        # User 1 should not be able to invite other members
        params = {
            'userId': self.users[2]['_id'],
            'level': AccessType.READ
        }
        resp = self.request(
            path='/group/%s/invite' % privateGroup['_id'], user=self.users[1],
            method='PUT', params=params)
        self.assertStatus(resp, 403)

        # We give user 1 write access
        self.groupModel.setUserAccess(privateGroup, self.users[1],
                                      AccessType.WRITE, save=True)

        # User 1 should not be able to invite anyone as admin
        params['level'] = AccessType.ADMIN
        resp = self.request(
            path='/group/%s/invite' % privateGroup['_id'], user=self.users[1],
            method='PUT', params=params)
        self.assertStatus(resp, 403)

        # User 1 should be able to invite someone with write access
        params['level'] = AccessType.WRITE
        resp = self.request(
            path='/group/%s/invite' % privateGroup['_id'], user=self.users[1],
            method='PUT', params=params)
        self.assertStatusOk(resp)

        # User 1 should not be able to remove a group admin
        params['userId'] = self.users[0]['_id']
        resp = self.request(
            path='/group/%s/remove' % privateGroup['_id'], user=self.users[1],
            method='PUT', params=params)
        self.assertStatus(resp, 403)
        self.assertEqual(resp.json['message'], 'Admin access denied for group.')

        # User 0 should be able to remove user 1
        params['userId'] = self.users[1]['_id']
        resp = self.request(
            path='/group/%s/remove' % privateGroup['_id'], user=self.users[0],
            method='PUT', params=params)
        self.assertStatusOk(resp)
        self.assertEqual(len(self.groupModel.getMembers(privateGroup)), 1)
