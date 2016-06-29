from girder.constants import AccessType
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

        self.users = [self.model('user').createUser(
            'usr%s' % num, 'passwd', 'tst', 'usr', 'u%s@u.com' % num)
            for num in [0, 1]]

    def testCuration(self):
        admin, user = self.users

        # create some groups
        g1 = self.model('group').createGroup('g1', admin)
        g2 = self.model('group').createGroup('g2', admin)
        g3 = self.model('group').createGroup('g3', admin)

        # set auto join rules
        rules = [
            {
                'pattern': '@kitware.com',
                'groupId': str(g1['_id']),
                'level': AccessType.ADMIN
            },
            {
                'pattern': '@example.com',
                'groupId': str(g2['_id']),
                'level': AccessType.READ
            },
            {
                'pattern': '@example.com',
                'groupId': str(g3['_id']),
                'level': AccessType.WRITE
            },
        ]
        params = {
            'list': json.dumps([{'key': 'autojoin', 'value': rules}])
        }
        resp = self.request(
            '/system/setting', user=admin, method='PUT', params=params)
        self.assertStatusOk(resp)

        # create users
        user1 = self.model('user').createUser(
            'user1', 'password', 'John', 'Doe', 'user1@example.com')
        user2 = self.model('user').createUser(
            'user2', 'password', 'John', 'Doe', 'user2@kitware.com')
        user3 = self.model('user').createUser(
            'user3', 'password', 'John', 'Doe', 'user3@kitware.co')

        # check correct groups were joined
        self.assertEqual(user1['groups'], [g2['_id'], g3['_id']])
        self.assertEqual(user2['groups'], [g1['_id']])
        self.assertEqual(user3['groups'], [])

        # check correct access levels
        g1 = self.model('group').load(g1['_id'], force=True)
        g2 = self.model('group').load(g2['_id'], force=True)
        g3 = self.model('group').load(g3['_id'], force=True)
        self.assertTrue(
            {u'id': user2['_id'], u'level': AccessType.ADMIN} in
            g1['access']['users'])
        self.assertTrue(
            {u'id': user1['_id'], u'level': AccessType.WRITE} in
            g3['access']['users'])
