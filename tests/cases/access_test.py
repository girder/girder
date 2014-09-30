#!/usr/bin/env python
# -*- coding: utf-8 -*-

###############################################################################
#  Copyright 2014 Kitware Inc.
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

from girder.api.rest import Resource
from girder.api import access


class AccessTestResource(Resource):
    def __init__(self):
        self.resourceName = 'accesstest'
        self.route('GET', ('default_access', ), self.defaultHandler)
        self.route('GET', ('admin_access', ), self.adminHandler)
        self.route('GET', ('user_access', ), self.userHandler)
        self.route('GET', ('public_access', ), self.publicHandler)

    # We deliberately don't have an access decorator
    def defaultHandler(self, **kwargs):
        return

    @access.admin
    def adminHandler(self, **kwargs):
        return

    @access.user
    def userHandler(self, **kwargs):
        return

    @access.public
    def publicHandler(self, **kwargs):
        return


def setUpModule():
    server = base.startServer()
    server.root.api.v1.accesstest = AccessTestResource()


def tearDownModule():
    base.stopServer()


class AccessTestCase(base.TestCase):
    def setUp(self):
        base.TestCase.setUp(self)

        admin = {
            'email': 'admin@email.com',
            'login': 'admin',
            'firstName': 'Admin',
            'lastName': 'Admin',
            'password': 'adminpassword',
            'admin': True
        }
        self.admin = self.model('user').createUser(**admin)

        user = {
            'email': 'good@email.com',
            'login': 'goodlogin',
            'firstName': 'First',
            'lastName': 'Last',
            'password': 'goodpassword',
            'admin': False
        }
        self.user = self.model('user').createUser(**user)

    def testAccessEndpoints(self):
        endpoints = [
            ("/accesstest/default_access", "admin"),
            ("/accesstest/admin_access", "admin"),
            ("/accesstest/user_access", "user"),
            ("/accesstest/public_access", "public")
        ]
        for endpoint in endpoints:
            resp = self.request(path=endpoint[0], method='GET', user=None)
            if endpoint[1] in ("public", ):
                self.assertStatusOk(resp)
            else:
                self.assertStatus(resp, 401)
            resp = self.request(path=endpoint[0], method='GET', user=self.user)
            if endpoint[1] in ("public", "user"):
                self.assertStatusOk(resp)
            else:
                self.assertStatus(resp, 403)
            resp = self.request(path=endpoint[0], method='GET', user=self.admin)
            if endpoint[1] in ("public", "user", "admin"):
                self.assertStatusOk(resp)
            else:
                self.assertStatus(resp, 403)
