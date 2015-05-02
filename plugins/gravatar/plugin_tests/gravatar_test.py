#!/usr/bin/env python
# -*- coding: utf-8 -*-

###############################################################################
#  Copyright Kitware Inc.
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

import hashlib

from girder import events
from server import PluginSettings
from tests import base


def setUpModule():
    base.enabledPlugins.append('gravatar')
    base.startServer()


def tearDown():
    base.stopServer()


class GravatarTest(base.TestCase):

    def setUp(self):
        # Since our plugin updates the model singleton, don't drop models
        base.TestCase.setUp(self, dropModels=False)

        self.admin = self.model('user').createUser(
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
        self.model('setting').set(PluginSettings.DEFAULT_IMAGE, 'mm')

        # Initially we should not have a gravatar_baseUrl value cached
        resp = self.request('/user/{}'.format(self.admin['_id']))
        self.assertStatusOk(resp)
        self.assertTrue('gravatar_baseUrl' not in resp.json)

        resp = self.request('/user/{}/gravatar'.format(self.admin['_id']),
                            isJson=False)
        md5 = hashlib.md5(self.admin['email'].encode()).hexdigest()
        self.assertRedirect(resp,
            'https://www.gravatar.com/avatar/{}?d=mm&s=64'.format(md5))

        # We should now have the gravatar_baseUrl cached on the user
        resp = self.request('/user/{}'.format(self.admin['_id']))
        self.assertStatusOk(resp)
        self.assertTrue('gravatar_baseUrl' in resp.json)

        # Update the user info without changing the email
        resp = self.request('/user/{}'.format(self.admin['_id']), method='PUT',
                            user=self.admin, params={
                                'firstName': 'first',
                                'lastName': 'last',
                                'email': self.admin['email']
                            })
        self.assertStatusOk(resp)

        # Cached value should still be there since we didn't change email
        self.assertTrue('gravatar_baseUrl' in resp.json)

        # Changing the email address should remove the cached value
        resp = self.request('/user/{}'.format(self.admin['_id']), method='PUT',
                            user=self.admin, params={
                                'firstName': 'first',
                                'lastName': 'last',
                                'email': 'new_email@email.com'
                            })
        self.assertStatusOk(resp)
        self.admin = self.model('user').load(self.admin['_id'], force=True)
        self.assertFalse('gravatar_baseUrl' in self.admin)
