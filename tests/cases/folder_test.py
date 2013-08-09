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

def setUpModule():
    base.startServer()

def tearDownModule():
    base.stopServer()

class FolderTestCase(base.TestCase):
    def setUp(self):
        base.TestCase.setUp(self)
        self.requireModels(['folder', 'user'])

    def testChildFolders(self):
        # First create a user. This will create default public and private folders.
        params = {
            'email' : 'good@email.com',
            'login' : 'goodlogin',
            'firstName' : 'First',
            'lastName' : 'Last',
            'password' : 'goodpassword'
            }
        user = self.userModel.createUser(**params)

        # We should only be able to see the public folder if we are anonymous
        resp = self.request(path='/folder', method='GET', params={
          'parentType' : 'user',
          'parentId' : user['_id']
          })
        self.assertEqual(len(resp.json), 1)

        # If we log in as the user, we should also be able to see the private folder
        resp = self.request(path='/folder', method='GET', user=user, params={
          'parentType' : 'user',
          'parentId' : user['_id']
          })
        self.assertEqual(len(resp.json), 2)

        # TODO a lot more testing here.

