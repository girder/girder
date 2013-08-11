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

class FolderTestCase(base.TestCase):
    def setUp(self):
        base.TestCase.setUp(self)
        self.requireModels(['folder', 'user'])

        user = {
            'email' : 'good@email.com',
            'login' : 'goodlogin',
            'firstName' : 'First',
            'lastName' : 'Last',
            'password' : 'goodpassword'
            }
        self.user = self.userModel.createUser(**user)

    def testChildFolders(self):
        # Test with some bad parameters
        resp = self.request(path='/folder', method='GET', params={})
        self.assertStatus(resp, 400)
        self.assertEqual(resp.json['message'], 'Invalid search mode.')

        resp = self.request(path='/folder', method='GET', params={
            'parentType' : 'invalid',
            'parentId' : self.user['_id']
            })
        self.assertStatus(resp, 400)
        self.assertEqual(resp.json['message'],
                         'The parentType must be user, community, or folder.')

        # We should only be able to see the public folder if we are anonymous
        resp = self.request(path='/folder', method='GET', params={
            'parentType' : 'user',
            'parentId' : self.user['_id']
            })
        self.assertStatusOk(resp)
        self.assertEqual(len(resp.json), 1)

        # If we log in as the user, we should also be able to see the private folder
        resp = self.request(path='/folder', method='GET', user=self.user, params={
            'parentType' : 'user',
            'parentId' : self.user['_id']
            })
        self.assertStatusOk(resp)
        self.assertEqual(len(resp.json), 2)

    def testCreateFolder(self):
        self.ensureRequiredParams(path='/folder', method='POST', required=['name', 'parentId'])

        # Grab the default user folders
        resp = self.request(path='/folder', method='GET', user=self.user, params={
            'parentType' : 'user',
            'parentId' : self.user['_id']
            })
        publicFolder = resp.json[0]
        privateFolder = resp.json[1]

        self.assertEqual(publicFolder['name'], 'Public')
        self.assertEqual(privateFolder['name'], 'Private')

        # Try to create a folder as anonymous; should fail
        resp = self.request(path='/folder', method='POST', params={
            'name' : 'a folder',
            'parentId' : publicFolder['_id']
            })
        self.assertAccessDenied(resp, AccessType.WRITE, 'folder')

        # Actually create subfolder under Public
        resp = self.request(path='/folder', method='POST', user=self.user, params={
            'name' : ' My public subfolder  ',
            'parentId' : publicFolder['_id']
            })
        self.assertStatusOk(resp)
        self.assertEqual(resp.json['parentId'], publicFolder['_id'])
        self.assertEqual(resp.json['parentCollection'], 'folder')
        self.assertTrue(resp.json['public'])

        # Now fetch the children of Public, we should see it
        resp = self.request(path='/folder', method='GET', user=self.user, params={
            'parentType' : 'folder',
            'parentId' : publicFolder['_id']
            })
        self.assertStatusOk(resp)
        self.assertEqual(len(resp.json), 1)
        self.assertEqual(resp.json[0]['name'], 'My public subfolder')

