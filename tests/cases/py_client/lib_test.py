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

import girder_client
import json
import mock
import os

# Need to set the environment variable before importing girder
os.environ['GIRDER_PORT'] = os.environ.get('GIRDER_TEST_PORT', '20200')  # noqa

from tests import base


def setUpModule():
    plugins = os.environ.get('ENABLED_PLUGINS', '')
    if plugins:
        base.enabledPlugins.extend(plugins.split())
    base.startServer(False)


def tearDownModule():
    base.stopServer()


class PythonClientTestCase(base.TestCase):

    def testRestCore(self):
        client = girder_client.GirderClient(port=os.environ['GIRDER_PORT'])

        # Register a user
        user = client.createResource('user', params={
            'firstName': 'First',
            'lastName': 'Last',
            'login': 'mylogin',
            'password': 'password',
            'email': 'email@email.com'
        })

        self.assertTrue(user['admin'])

        # Test authentication with bad args
        flag = False
        try:
            client.authenticate()
        except Exception:
            flag = True

        self.assertTrue(flag)

        # Test authentication failure
        flag = False
        try:
            client.authenticate(username=user['login'], password='wrong')
        except girder_client.AuthenticationError:
            flag = True

        self.assertTrue(flag)

        # Interactive login (successfully)
        with mock.patch('girder_client.rawInput', return_value=user['login']),\
                mock.patch('getpass.getpass', return_value='password'):
            client.authenticate(interactive=True)

        # /user/me should now return our user info
        user = client.getResource('user/me')
        self.assertEqual(user['login'], 'mylogin')

        # Test HTTP error case
        flag = False
        try:
            client.getResource('user/badId')
        except girder_client.HttpError as e:
            self.assertEqual(e.status, 400)
            self.assertEqual(e.method, 'GET')
            resp = json.loads(e.responseText)
            self.assertEqual(resp['type'], 'validation')
            self.assertEqual(resp['field'], 'id')
            self.assertEqual(resp['message'], 'Invalid ObjectId: badId')
            flag = True

        self.assertTrue(flag)

        # Test some folder routes
        folders = client.listFolder(
            parentId=user['_id'], parentFolderType='user')
        self.assertEqual(len(folders), 2)

        privateFolder = publicFolder = None
        for folder in folders:
            if folder['name'] == 'Public':
                publicFolder = folder
            elif folder['name'] == 'Private':
                privateFolder = folder

        self.assertNotEqual(privateFolder, None)
        self.assertNotEqual(publicFolder, None)

        self.assertEqual(client.getFolder(privateFolder['_id']), privateFolder)

        acl = client.getFolderAccess(privateFolder['_id'])
        self.assertIn('users', acl)
        self.assertIn('groups', acl)

        client.setFolderAccess(privateFolder['_id'], json.dumps(acl),
                               public=False)
        self.assertEqual(acl, client.getFolderAccess(privateFolder['_id']))

        # Test recursive ACL propagation (not very robust test yet)
        subfolder = client.createFolder(privateFolder['_id'], name='Subfolder')
        client.inheritAccessControlRecursive(privateFolder['_id'])
