# -*- coding: utf-8 -*-
from .. import base
from girder.constants import AccessType
from girder.models.folder import Folder
from girder.models.group import Group
from girder.models.setting import Setting
from girder.models.user import User
from girder.settings import SettingKey


def setUpModule():
    base.startServer()


def tearDownModule():
    base.stopServer()


class GroupTestCase(base.TestCase):
    def setUp(self):
        super().setUp()

        # Create a set of users so we can work with these groups.  User 0 is
        # an admin
        self.users = [User().createUser(
            'usr%s' % num, 'passwd', 'tst', 'usr', 'u%s@girder.test' % num)
            for num in range(6)]

    def testDirectAdd(self):
        """
        Tests the functionality of an admin user adding a user directly to
        a group, bypassing the invitation process.
        """
        group = Group().createGroup('g1', self.users[0])
        self.assertFalse(Group().hasAccess(group, self.users[1], AccessType.WRITE))

        # Admin user can add user 1 directly if they pass force=True.
        resp = self.request(path='/group/%s/invitation' % group['_id'],
                            method='POST', user=self.users[0],
                            params={
                                'force': 'true',
                                'userId': self.users[1]['_id'],
                                'level': AccessType.WRITE
                                })
        self.assertStatus(resp, 200)
        user1 = User().load(self.users[1]['_id'], force=True)
        group = Group().load(group['_id'], force=True)
        self.assertTrue(Group().hasAccess(group, user1, AccessType.WRITE))
        self.assertFalse(Group().hasAccess(group, user1, AccessType.ADMIN))
        self.assertTrue(group['_id'] in user1['groups'])

        # User 1 should not be able to use the force option.
        resp = self.request(path='/group/%s/invitation' % group['_id'],
                            method='POST', user=self.users[1],
                            params={
                                'force': 'true',
                                'userId': self.users[2]['_id']
                                })
        self.assertStatus(resp, 403)
        self.assertEqual(resp.json['message'], 'Administrator access required.')
        user2 = User().load(self.users[2]['_id'], force=True)
        self.assertFalse(group['_id'] in user2.get('groups', ()))

    def testDeleteGroupDeletesAccessReferences(self):
        """
        This test ensures that when a group is deleted, references to it in
        various access-control lists are also removed.
        """
        # Create a couple of groups
        group1 = Group().createGroup('g1', self.users[0])
        group2 = Group().createGroup('g2', self.users[0])

        # Create a folder and give both groups some access on it
        folder = Folder().createFolder(
            parent=self.users[0], name='x', parentType='user', public=False,
            creator=self.users[0])
        Folder().setGroupAccess(folder, group1, AccessType.WRITE)
        Folder().setGroupAccess(folder, group2, AccessType.READ)
        folder = Folder().save(folder)

        self.assertEqual(len(folder['access']['groups']), 2)

        # Delete group 1; folder access list should no longer contain it
        Group().remove(group1)
        group1 = Group().load(group1['_id'])
        folder = Folder().load(folder['_id'], force=True)

        self.assertEqual(group1, None)
        self.assertEqual(len(folder['access']['groups']), 1)

    def testGetGroups(self):
        """
        Test the GET endpoints for groups, including getting a single
        group and getting the list of all groups.
        """
        privateGroup = Group().createGroup('private ', self.users[0], public=False)
        publicGroup = Group().createGroup('public ', self.users[0], public=True)

        # Error: Invalid GET URL
        resp = self.request(path='/group/%s/foo' % publicGroup['_id'], method='GET')
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

        # The same rules apply to the group access points
        resp = self.request(
            path='/group/%s/access' % publicGroup['_id'], method='GET')
        self.assertStatusOk(resp)
        resp = self.request(
            path='/group/%s/access' % privateGroup['_id'], method='GET')
        self.assertStatus(resp, 401)
        resp = self.request(
            path='/group/%s/access' % privateGroup['_id'], method='GET',
            user=self.users[0])
        self.assertStatusOk(resp)

        # Test listing all groups
        privateGroup2 = Group().createGroup('private group', self.users[0], public=False)
        resp = self.request(path='/group', method='GET', user=self.users[0])
        self.assertStatusOk(resp)
        self.assertIsInstance(resp.json, list)
        self.assertEqual(len(resp.json), 3)

        resp = self.request(path='/group', method='GET', user=self.users[1])
        self.assertStatusOk(resp)
        self.assertIsInstance(resp.json, list)
        self.assertEqual(len(resp.json), 1)
        self.assertEqual(resp.json[0]['_id'], str(publicGroup['_id']))
        # Test searching by name
        resp = self.request(path='/group', method='GET', user=self.users[0],
                            params={'text': 'private'})
        self.assertStatusOk(resp)
        self.assertIsInstance(resp.json, list)
        self.assertEqual(len(resp.json), 2)
        self.assertEqual(resp.json[0]['_id'], str(privateGroup['_id']))
        self.assertEqual(resp.json[1]['_id'], str(privateGroup2['_id']))
        resp = self.request(path='/group', method='GET', user=self.users[0],
                            params={'text': 'private', 'exact': True})
        self.assertStatusOk(resp)
        self.assertIsInstance(resp.json, list)
        self.assertEqual(len(resp.json), 1)
        self.assertEqual(resp.json[0]['_id'], str(privateGroup['_id']))

    def testUpdateGroup(self):
        """
        Test editing the properties of a group.
        """
        group = Group().createGroup('public ', self.users[0], public=True)

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

        resp = self.request(path='/group/%s' % group['_id'],
                            method='PUT', user=self.users[0], params=params)
        self.assertStatusOk(resp)

        group = Group().load(group['_id'], force=True)
        self.assertEqual(group['public'], False)
        self.assertEqual(group['name'], params['name'].strip())
        self.assertEqual(group['description'], params['description'].strip())

    def testGroupAccess(self):
        """
        Test creation, invitation, joining, and removing of users from
        groups.
        """
        self.ensureRequiredParams(
            path='/group', method='POST', required=['name'], user=self.users[0])

        params = {
            'name': ' A group name ',
            'description': 'my description ',
            'public': 'true'
        }

        # Anonymous users can't make groups
        resp = self.request(path='/group', method='POST', params=params)
        self.assertStatus(resp, 401)
        self.assertEqual('You must be logged in.', resp.json['message'])

        # Have user 0 make a public group
        resp = self.request(path='/group', method='POST', params=params,
                            user=self.users[0])
        self.assertStatusOk(resp)
        self.assertEqual(resp.json['name'], params['name'].strip())
        self.assertEqual(resp.json['description'],
                         params['description'].strip())

        publicGroup = Group().load(resp.json['_id'], force=True)

        # User 1 should be able to see the public group
        self.assertTrue(Group().hasAccess(publicGroup, self.users[0], AccessType.ADMIN))
        self.assertTrue(Group().hasAccess(publicGroup, self.users[1], AccessType.READ))

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
        privateGroup = Group().load(resp.json['_id'], force=True)

        # User 1 should not be able to see it
        self.assertTrue(Group().hasAccess(privateGroup, self.users[0], AccessType.ADMIN))
        self.assertFalse(Group().hasAccess(privateGroup, self.users[1], AccessType.READ))

        self.assertEqual(len(list(Group().getMembers(privateGroup))), 1)

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
            path='/group/%s/invitation' % privateGroup['_id'],
            user=self.users[0], method='GET')
        self.assertStatusOk(resp)
        self.assertEqual(len(resp.json), 1)
        self.assertEqual(resp.json[0]['_id'], str(self.users[1]['_id']))

        # An email should have been sent
        self.assertTrue(base.mockSmtp.waitForMail())

        # Reload user and group since they've changed in the database
        self.users[1] = User().load(self.users[1]['_id'], force=True)
        privateGroup = Group().load(privateGroup['_id'], force=True)

        # User object should now have an invitation set on it
        self.assertTrue(privateGroup['_id'] in [
            invite['groupId'] for invite in self.users[1]['groupInvites']])

        # User 1 should now be able to see the group, but should not be in it.
        self.assertTrue(Group().hasAccess(privateGroup, self.users[1], AccessType.READ))
        self.assertEqual(len(list(Group().getMembers(privateGroup))), 1)

        # Removing user 1 from the group before they join it should remove the
        # invitation.
        resp = self.request(
            path='/group/%s/member' % privateGroup['_id'], user=self.users[0],
            method='DELETE', params={'userId': self.users[1]['_id']})
        self.assertStatusOk(resp)
        self.users[1] = User().load(self.users[1]['_id'], force=True)
        self.assertEqual(0, len(self.users[1]['groupInvites']))

        # Now re-invite user 1
        resp = self.request(
            path='/group/%s/invitation' % privateGroup['_id'],
            user=self.users[0], method='POST', params=params)
        self.assertStatusOk(resp)

        # User 1 should not yet be in the member list
        resp = self.request(
            path='/group/%s/member' % privateGroup['_id'],
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
            path='/group/%s/member' % privateGroup['_id'],
            user=self.users[0], method='GET')
        self.assertStatusOk(resp)
        self.assertEqual(len(resp.json), 2)
        self.assertEqual(resp.json[1]['_id'], str(self.users[1]['_id']))

        # Reload user and group since they've changed in the database
        self.users[1] = User().load(self.users[1]['_id'], force=True)
        privateGroup = Group().load(privateGroup['_id'], force=True)

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
            path='/group/%s/moderator' % privateGroup['_id'],
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
            path='/group/%s/invitation' % privateGroup['_id'],
            user=self.users[1], method='POST', params=params)
        self.assertStatusOk(resp)

        # Have user 2 join the group
        resp = self.request(
            path='/group/%s/member' % privateGroup['_id'], method='POST',
            user=self.users[2])
        self.assertStatusOk(resp)

        # User 1 should not be able to remove a group admin
        params['userId'] = self.users[0]['_id']
        resp = self.request(
            path='/group/%s/member' % privateGroup['_id'], user=self.users[1],
            method='DELETE', params=params)
        self.assertStatus(resp, 403)
        self.assertTrue(resp.json['message'].startswith(
            'Admin access denied for group'))

        # User 1 should not be able to delete the group
        resp = self.request(
            path='/group/%s' % privateGroup['_id'], user=self.users[1],
            method='DELETE')
        self.assertStatus(resp, 403)
        self.assertTrue(resp.json['message'].startswith(
            'Admin access denied for group'))

        # We promote user 1 to admin
        resp = self.request(
            path='/group/%s/admin' % privateGroup['_id'],
            user=self.users[0], method='POST', params={
                'userId': self.users[1]['_id']
            })
        self.assertStatusOk(resp)
        privateGroup = Group().load(privateGroup['_id'], force=True)
        self.assertTrue(Group().hasAccess(privateGroup, self.users[1], AccessType.ADMIN))

        # User 1 should now be able to promote and demote members
        resp = self.request(
            path='/group/%s/admin' % privateGroup['_id'],
            user=self.users[1], method='POST', params={
                'userId': self.users[2]['_id']
            })
        self.assertStatusOk(resp)
        privateGroup = Group().load(privateGroup['_id'], force=True)
        self.assertTrue(Group().hasAccess(privateGroup, self.users[2], AccessType.ADMIN))

        resp = self.request(
            path='/group/%s/admin' % privateGroup['_id'],
            user=self.users[1], method='DELETE', params={
                'userId': self.users[2]['_id']
            })
        self.assertStatusOk(resp)
        privateGroup = Group().load(privateGroup['_id'], force=True)
        self.assertFalse(Group().hasAccess(privateGroup, self.users[2], AccessType.ADMIN))

        # User 2 should be able to leave the group
        self.users[2] = User().load(self.users[2]['_id'], force=True)
        self.assertTrue(privateGroup['_id'] in self.users[2]['groups'])
        resp = self.request(
            path='/group/%s/member' % privateGroup['_id'],
            user=self.users[2], method='DELETE')
        self.assertStatusOk(resp)
        self.users[2] = User().load(self.users[2]['_id'], force=True)
        self.assertFalse(privateGroup['_id'] in self.users[2]['groups'])

        # User 0 should be able to remove user 1
        params['userId'] = self.users[1]['_id']
        self.assertEqual(
            len(list(Group().getMembers(privateGroup))), 2)
        resp = self.request(
            path='/group/%s/member' % privateGroup['_id'], user=self.users[0],
            method='DELETE', params=params)
        self.assertStatusOk(resp)
        self.assertEqual(len(list(Group().getMembers(privateGroup))), 1)

        # User 0 should be able to delete the group
        self.users[0] = User().load(self.users[0]['_id'], force=True)
        self.assertEqual(len(self.users[0]['groups']), 2)
        resp = self.request(
            path='/group/%s' % privateGroup['_id'], user=self.users[0],
            method='DELETE')
        self.assertStatusOk(resp)
        self.assertEqual(resp.json['message'],
                         'Deleted the group %s.' % privateGroup['name'])
        privateGroup = Group().load(privateGroup['_id'], force=True)
        self.assertTrue(privateGroup is None)

        # Make sure group reference was removed from user 0
        self.users[0] = User().load(self.users[0]['_id'], force=True)
        self.assertEqual(len(self.users[0]['groups']), 1)

    def testGroupAddAllow(self):
        """
        Test letting group admins and mods ability to add users directly to
        groups.
        """
        policy = {
            'never': {
                'default': [0],
                'no': [0],
                'yesadmin': [0],
                'yesmod': [0],
            },
            'noadmin': {
                'default': [0],
                'no': [0],
                'yesadmin': [0, 1],
                'yesmod': [0, 1],
            },
            'nomod': {
                'default': [0],
                'no': [0],
                'yesadmin': [0, 1],
                'yesmod': [0, 1, 2],
            },
            'yesadmin': {
                'default': [0, 1],
                'no': [0],
                'yesadmin': [0, 1],
                'yesmod': [0, 1],
            },
            'yesmod': {
                'default': [0, 1, 2],
                'no': [0],
                'yesadmin': [0, 1],
                'yesmod': [0, 1, 2],
            },
        }
        # We want the group to have user 1 as a group admin, user 2 as a group
        # moderator, and user 3 as a group member.  user 0 is a sys admin, and
        # user 4 is not part of the group.  User 5 is the user who is added to
        # the group.
        group = Group().createGroup('public ', self.users[0], public=True)
        for user in [1, 2, 3]:
            resp = self.request(
                path='/group/%s/invitation' % group['_id'],
                params={
                    'force': 'true',
                    'userId': self.users[user]['_id'],
                    'level': 3 - user
                }, method='POST', user=self.users[0])
            self.assertStatusOk(resp)
        resp = self.request(
            path='/group/%s/member' % group['_id'], user=self.users[0],
            method='DELETE', params={'userId': self.users[0]['_id']})
        self.assertStatusOk(resp)
        for systemSetting in policy:
            Setting().set(SettingKey.ADD_TO_GROUP_POLICY, systemSetting)
            for groupSetting in policy[systemSetting]:
                resp = self.request(
                    path='/group/%s' % group['_id'], user=self.users[0],
                    method='PUT', params={'addAllowed': groupSetting})
                self.assertStatusOk(resp)
                for user in range(5):
                    resp = self.request(
                        path='/group/%s/invitation' % group['_id'],
                        params={
                            'force': 'true',
                            'userId': self.users[5]['_id'],
                        }, method='POST', user=self.users[user])
                    if user in policy[systemSetting][groupSetting]:
                        self.assertStatusOk(resp)
                    else:
                        self.assertStatus(resp, 403)
        Setting().unset(SettingKey.ADD_TO_GROUP_POLICY)
