from girder.constants import AccessType
from girder.models.group import Group
from girder.models.user import User
from tests import base
import json


def setUpModule():
    base.enabledPlugins.append('autojoin')
    base.startServer()


def tearDownModule():
    base.stopServer()


class AutoJoinTest(base.TestCase):

    def setUp(self):
        base.TestCase.setUp(self)

        self.users = [User().createUser(
            'usr%s' % num, 'passwd', 'tst', 'usr', 'u%s@girder4.test' % num)
            for num in [0, 1]]

    def testAutoJoinBehavior(self):
        admin, user = self.users

        # create some groups
        g1 = Group().createGroup('g1', admin)
        g2 = Group().createGroup('g2', admin)
        g3 = Group().createGroup('g3', admin)

        # set auto join rules
        rules = [
            {
                'pattern': '@girder2.test',
                'groupId': str(g1['_id']),
                'level': AccessType.ADMIN
            },
            {
                'pattern': '@girder1.test',
                'groupId': str(g2['_id']),
                'level': AccessType.READ
            },
            {
                'pattern': '@girder1.test',
                'groupId': str(g3['_id']),
                'level': AccessType.WRITE
            },
        ]
        params = {
            'list': json.dumps([{'key': 'autojoin', 'value': rules}])
        }
        resp = self.request('/system/setting', user=admin, method='PUT', params=params)
        self.assertStatusOk(resp)

        # create users
        user1 = User().createUser('user1', 'password', 'John', 'Doe', 'user1@girder1.test')
        user2 = User().createUser('user2', 'password', 'John', 'Doe', 'user2@girder2.test')
        user3 = User().createUser('user3', 'password', 'John', 'Doe', 'user3@girder3.test')

        # check correct groups were joined
        self.assertEqual(user1['groups'], [g2['_id'], g3['_id']])
        self.assertEqual(user2['groups'], [g1['_id']])
        self.assertEqual(user3['groups'], [])

        # check correct access levels
        g1 = Group().load(g1['_id'], force=True)
        g3 = Group().load(g3['_id'], force=True)
        self.assertIn(
            {'id': user2['_id'], 'level': AccessType.ADMIN, 'flags': []},
            g1['access']['users'])
        self.assertIn(
            {'id': user1['_id'], 'level': AccessType.WRITE, 'flags': []},
            g3['access']['users'])
