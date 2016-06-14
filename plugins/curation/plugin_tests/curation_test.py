#!/usr/bin/env python
# -*- coding: utf-8 -*-

###############################################################################
#  Copyright 2016 Kitware Inc.
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

from girder.constants import AccessType
from tests import base


def setUpModule():
    base.enabledPlugins.append('curation')
    base.startServer()


def tearDownModule():
    base.stopServer()


class CurationTest(base.TestCase):

    def setUp(self):
        base.TestCase.setUp(self)

        self.users = [self.model('user').createUser(
            'usr%s' % num, 'passwd', 'tst', 'usr', 'u%s@u.com' % num)
            for num in [0, 1]]

    def testCuration(self):
        admin, user = self.users

        # create a collection and a folder
        c1 = self.model('collection').createCollection(
            'c1', admin, public=True)
        f1 = self.model('folder').createFolder(
            c1, 'f1', parentType='collection', public=False)
        f2 = self.model('folder').createFolder(
            c1, 'f2', parentType='collection', public=False)
        self.model('folder').setUserAccess(f2, user, AccessType.WRITE, True)

        # test initial curation values
        path = '/folder/%s/curation' % f1.get('_id')
        resp = self.request(path=path, user=admin)
        self.assertStatusOk(resp)
        self.assertEqual(resp.json['enabled'], False)
        self.assertEqual(resp.json['timeline'], [])

        # test non-admin access to private folder
        path = '/folder/%s/curation' % f1.get('_id')
        resp = self.request(path=path, user=user)
        self.assertStatus(resp, 403)

        # test non-admin access to folder with permissions
        path = '/folder/%s/curation' % f2.get('_id')
        resp = self.request(path=path, user=user)
        self.assertStatusOk(resp)
        self.assertEqual(resp.json['enabled'], False)
        self.assertEqual(resp.json['timeline'], [])

        # test non-admin unable to enable curation
        path = '/folder/%s/curation' % f2.get('_id')
        params = dict(enabled='true')
        resp = self.request(path=path, user=user, method='PUT', params=params)
        self.assertStatus(resp, 403)

        # test admin able to enable curation
        path = '/folder/%s/curation' % f2.get('_id')
        params = dict(enabled='true')
        resp = self.request(path=path, user=admin, method='PUT', params=params)
        self.assertStatusOk(resp)
        self.assertEqual(resp.json['enabled'], True)
        self.assertEqual(resp.json['status'], 'construction')

        # test non-admin unable to disable curation
        path = '/folder/%s/curation' % f2.get('_id')
        params = dict(enabled='false')
        resp = self.request(path=path, user=user, method='PUT', params=params)
        self.assertStatus(resp, 403)

        # test non-admin able to request approval
        path = '/folder/%s/curation' % f2.get('_id')
        params = dict(status='requested')
        resp = self.request(path=path, user=user, method='PUT', params=params)
        self.assertStatusOk(resp)
        self.assertEqual(resp.json['enabled'], True)
        self.assertEqual(resp.json['status'], 'requested')

        # test non-admin unable to change status
        path = '/folder/%s/curation' % f2.get('_id')
        params = dict(status='approved')
        resp = self.request(path=path, user=user, method='PUT', params=params)
        self.assertStatus(resp, 403)

        path = '/folder/%s/curation' % f2.get('_id')
        params = dict(status='construction')
        resp = self.request(path=path, user=user, method='PUT', params=params)
        self.assertStatus(resp, 403)

        # test admin able to approve
        path = '/folder/%s/curation' % f2.get('_id')
        params = dict(status='approved')
        resp = self.request(path=path, user=admin, method='PUT', params=params)
        self.assertStatusOk(resp)
        self.assertEqual(resp.json['enabled'], True)
        self.assertEqual(resp.json['status'], 'approved')

        # test timeline is correct
        path = '/folder/%s/curation' % f2.get('_id')
        resp = self.request(path=path, user=user)
        self.assertStatusOk(resp)
        self.assertEqual(len(resp.json['timeline']), 3)
        self.assertEqual(resp.json['timeline'][0]['oldEnabled'], False)
        self.assertEqual(resp.json['timeline'][0]['enabled'], True)
        self.assertEqual(resp.json['timeline'][0]['oldStatus'], 'construction')
        self.assertEqual(resp.json['timeline'][0]['status'], 'construction')
        self.assertEqual(resp.json['timeline'][1]['oldEnabled'], True)
        self.assertEqual(resp.json['timeline'][1]['enabled'], True)
        self.assertEqual(resp.json['timeline'][1]['oldStatus'], 'construction')
        self.assertEqual(resp.json['timeline'][1]['status'], 'requested')
        self.assertEqual(resp.json['timeline'][2]['oldEnabled'], True)
        self.assertEqual(resp.json['timeline'][2]['enabled'], True)
        self.assertEqual(resp.json['timeline'][2]['oldStatus'], 'requested')
        self.assertEqual(resp.json['timeline'][2]['status'], 'approved')
