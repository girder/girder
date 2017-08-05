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

from girder.constants import SettingKey

from tests import base


def setUpModule():
    base.enabledPlugins.append('terms')
    base.startServer()


def tearDownModule():
    base.stopServer()


class TermsTest(base.TestCase):
    def setUp(self):
        base.TestCase.setUp(self)

        self.siteAdminUser = self.model('user').createUser(
            email='rocky@phila.pa.us',
            login='rocky',
            firstName='Robert',
            lastName='Balboa',
            password='adrian'
        )
        self.creatorUser = self.model('user').createUser(
            email='creed@la.ca.us',
            login='creed',
            firstName='Apollo',
            lastName='Creed',
            password='the1best'
        )
        creationSetting = self.model('setting').getDefault(SettingKey.COLLECTION_CREATE_POLICY)
        creationSetting['open'] = True
        self.model('setting').set(SettingKey.COLLECTION_CREATE_POLICY, creationSetting)

    def testTerms(self):
        # Ensure that ordinary collections still work
        resp = self.request('/collection', method='POST', user=self.creatorUser, params={
            'name': 'Basic Collection',
            'description': 'Some description.',
            'public': True
        })
        self.assertStatusOk(resp)
        self.assertDictContainsSubset({
            'name': 'Basic Collection',
            'description': 'Some description.',
            'public': True,
            'size': 0,
            '_modelType': 'collection',
            'terms': None
        }, resp.json)
        basicCollectionId = resp.json['_id']

        # Try to accept the terms, on a collection with no terms
        resp = self.request(
            '/collection/%s/acceptTerms' % basicCollectionId, method='POST', user=self.creatorUser,
            params={
                # This is the hash of an empty string
                'termsHash': '47DEQpj8HBSa+/TImW+5JCeuQeRkm5NMpJWZG3hSuFU='
            })
        self.assertStatus(resp, 400)

        # Create a collection with unicode terms
        resp = self.request('/collection', method='POST', user=self.creatorUser, params={
            'name': 'Terms Collection',
            'description': 'Some other description.',
            'public': True,
            'terms': u'# Sample Terms of Use\n\n**\u00af\\\\\\_(\u30c4)\\_/\u00af**'.encode('utf-8')
        })
        self.assertStatusOk(resp)
        self.assertDictContainsSubset({
            'name': 'Terms Collection',
            'description': 'Some other description.',
            'public': True,
            'size': 0,
            '_modelType': 'collection',
            'terms': u'# Sample Terms of Use\n\n**\u00af\\\\\\_(\u30c4)\\_/\u00af**'
        }, resp.json)
        termsCollectionId = resp.json['_id']

        # Fetch the terms on a collection, ensuring they're saved
        resp = self.request(
            '/collection/%s' % termsCollectionId, method='GET', user=self.creatorUser)
        self.assertStatusOk(resp)
        self.assertDictContainsSubset({
            'name': 'Terms Collection',
            'description': 'Some other description.',
            'public': True,
            'size': 0,
            '_modelType': 'collection',
            'terms': u'# Sample Terms of Use\n\n**\u00af\\\\\\_(\u30c4)\\_/\u00af**'
        }, resp.json)

        # Ensure that the user has not yet accepted any terms
        resp = self.request('/user/me', method='GET', user=self.creatorUser)
        self.assertStatusOk(resp)
        self.assertNotHasKeys(resp.json, {'terms'})

        # Try to accept the terms, with the wrong hash
        resp = self.request(
            '/collection/%s/acceptTerms' % termsCollectionId, method='POST', user=self.creatorUser,
            params={
                'termsHash': 'gargTz1mz476PQf9oUVbtob7OS3ban/3aHqOdLgcHA0='.replace('g', 'f')
            })
        self.assertStatus(resp, 400)

        # Accept the terms
        resp = self.request(
            '/collection/%s/acceptTerms' % termsCollectionId, method='POST', user=self.creatorUser,
            params={
                'termsHash': 'gargTz1mz476PQf9oUVbtob7OS3ban/3aHqOdLgcHA0='
            })
        self.assertStatusOk(resp)

        # Check that the user has accepted the terms
        resp = self.request('/user/me', method='GET', user=self.creatorUser)
        self.assertStatusOk(resp)
        self.assertDictContainsSubset(
            {'hash': 'gargTz1mz476PQf9oUVbtob7OS3ban/3aHqOdLgcHA0='},
            resp.json.get('terms', {}).get('collection', {}).get(termsCollectionId, {})
        )

        # Ensure that other users cannot read term acceptances
        resp = self.request('/user/%s' % self.creatorUser['_id'], method='GET')
        self.assertStatusOk(resp)
        self.assertNotHasKeys(resp.json, {'terms'})

        # Modify a collection to have new terms
        resp = self.request(
            '/collection/%s' % termsCollectionId, method='PUT', user=self.creatorUser, params={
                'description': 'A new description.',
                'terms': '# New Terms of Use\n\nThese have changed.'
            })
        self.assertStatusOk(resp)
        self.assertDictContainsSubset({
            'name': 'Terms Collection',
            'description': 'A new description.',
            'public': True,
            'size': 0,
            '_modelType': 'collection',
            'terms': '# New Terms of Use\n\nThese have changed.'
        }, resp.json)

        # Fetch the terms on a collection, while anonymous
        resp = self.request('/collection/%s' % termsCollectionId, method='GET')
        self.assertStatusOk(resp)
        self.assertDictContainsSubset({
            'name': 'Terms Collection',
            'description': 'A new description.',
            'public': True,
            'size': 0,
            '_modelType': 'collection',
            'terms': '# New Terms of Use\n\nThese have changed.'
        }, resp.json)
