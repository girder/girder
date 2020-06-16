# -*- coding: utf-8 -*-
from girder.models.setting import Setting
from girder.models.user import User
from girder.settings import SettingKey

from tests import base


def setUpModule():
    base.enabledPlugins.append('terms')
    base.startServer()


def tearDownModule():
    base.stopServer()


class TermsTest(base.TestCase):
    def setUp(self):
        super().setUp()

        self.siteAdminUser = User().createUser(
            email='rocky@phila.pa.us',
            login='rocky',
            firstName='Robert',
            lastName='Balboa',
            password='adrian'
        )
        self.creatorUser = User().createUser(
            email='creed@la.ca.us',
            login='creed',
            firstName='Apollo',
            lastName='Creed',
            password='the1best'
        )
        creationSetting = Setting().getDefault(SettingKey.COLLECTION_CREATE_POLICY)
        creationSetting['open'] = True
        Setting().set(SettingKey.COLLECTION_CREATE_POLICY, creationSetting)

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
                'termsHash': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'
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
                'termsHash':
                    '81aae04f3d66cf8efa3d07fda1455bb686fb392ddb6a7ff7687a8e74b81c1c0d'
                    .replace('8', '2')
            })
        self.assertStatus(resp, 400)

        # Accept the terms
        resp = self.request(
            '/collection/%s/acceptTerms' % termsCollectionId, method='POST', user=self.creatorUser,
            params={
                'termsHash': '81aae04f3d66cf8efa3d07fda1455bb686fb392ddb6a7ff7687a8e74b81c1c0d'
            })
        self.assertStatusOk(resp)

        # Check that the user has accepted the terms
        resp = self.request('/user/me', method='GET', user=self.creatorUser)
        self.assertStatusOk(resp)
        self.assertDictContainsSubset(
            {'hash': '81aae04f3d66cf8efa3d07fda1455bb686fb392ddb6a7ff7687a8e74b81c1c0d'},
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
