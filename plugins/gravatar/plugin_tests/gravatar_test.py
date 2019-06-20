# -*- coding: utf-8 -*-
import hashlib

from tests import base
from girder.models.setting import Setting
from girder.models.user import User

from girder_gravatar import PluginSettings


def setUpModule():
    base.enabledPlugins.append('gravatar')
    base.startServer()


def tearDown():
    base.stopServer()


class GravatarTest(base.TestCase):

    def setUp(self):
        # Since our plugin updates the model singleton, don't drop models
        base.TestCase.setUp(self, dropModels=False)

        self.admin = User().createUser(
            email='not.a.real.email@mail.com',
            login='admin',
            firstName='first',
            lastName='last',
            password='password',
            admin=True
        )

    def tearDown(self):
        base.stopServer()

    def testGravatarUrlComputation(self):
        """
        Tests that our caching of gravatar URLs works as expected.
        """
        Setting().set(PluginSettings.DEFAULT_IMAGE, 'mm')

        # Gravatar base URL should be computed on user creation
        resp = self.request('/user/%s' % self.admin['_id'])
        self.assertStatusOk(resp)
        self.assertTrue('gravatar_baseUrl' in resp.json)

        resp = self.request('/user/%s/gravatar' % str(self.admin['_id']), isJson=False)
        md5 = hashlib.md5(self.admin['email'].encode()).hexdigest()
        self.assertRedirect(
            resp,
            'https://www.gravatar.com/avatar/%s?d=identicon&s=64' % md5)

        # We should now have the gravatar_baseUrl cached on the user
        resp = self.request('/user/%s' % self.admin['_id'])
        self.assertStatusOk(resp)
        self.assertTrue('gravatar_baseUrl' in resp.json)
        oldBaseUrl = resp.json['gravatar_baseUrl']

        # Changing the email address should change the cached value
        resp = self.request(
            '/user/%s' % self.admin['_id'], method='PUT', user=self.admin,
            params={
                'firstName': 'first',
                'lastName': 'last',
                'email': 'new_email@email.com'
            })
        self.assertStatusOk(resp)
        self.admin = User().load(self.admin['_id'], force=True)
        self.assertNotEqual(self.admin['gravatar_baseUrl'], oldBaseUrl)

        # Make sure we picked up the new default setting
        resp = self.request('/user/%s/gravatar' % str(self.admin['_id']), isJson=False)
        md5 = hashlib.md5(self.admin['email'].encode()).hexdigest()
        self.assertRedirect(
            resp,
            'https://www.gravatar.com/avatar/%s?d=mm&s=64' % md5)

    def testUserInfoUpdate(self):
        user = User().createUser(
            email='normaluser@mail.com',
            login='normal',
            firstName='normal',
            lastName='normal',
            password='password',
            admin=False
        )

        resp = self.request(
            '/user/%s' % str(user['_id']), method='PUT', user=user,
            params={
                'email': 'newemail@mail.com',
                'firstName': 'normal',
                'lastName': 'normal'
            })
        self.assertStatusOk(resp)
