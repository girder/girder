# -*- coding: utf-8 -*-
import os

from tests import base
from girder.constants import ROOT_DIR
from girder.models.folder import Folder
from girder.models.user import User


def setUpModule():
    base.enabledPlugins.append('readme')
    base.startServer()


def tearDownModule():
    base.stopServer()


class ReadmeTestCase(base.TestCase):
    def setUp(self):
        base.TestCase.setUp(self)

        # Create some test documents with an item
        admin = {
            'email': 'admin@girder.test',
            'login': 'adminlogin',
            'firstName': 'Admin',
            'lastName': 'Last',
            'password': 'adminpassword',
            'admin': True,
        }
        self.admin = User().createUser(**admin)

        user = {
            'email': 'good@girder.test',
            'login': 'goodlogin',
            'firstName': 'First',
            'lastName': 'Last',
            'password': 'goodpassword',
            'admin': False,
        }
        self.user = User().createUser(**user)

        folders = Folder().childFolders(
            parent=self.admin, parentType='user', user=self.admin
        )
        for folder in folders:
            if folder['public'] is True:
                self.publicFolder = folder
            else:
                self.privateFolder = folder

        path = os.path.join(
            ROOT_DIR, 'plugins', 'readme', 'plugin_tests', 'data', 'README.md',
        )
        with open(path, 'rb') as file:
            self.readmeMarkdown = file.read()

    def testReadme(self):
        # Upload the README.md to the admin's private folder
        resp = self.request(
            path='/file',
            method='POST',
            user=self.admin,
            params={
                'parentType': 'folder',
                'parentId': self.privateFolder['_id'],
                'name': 'README.md',
                'size': len(self.readmeMarkdown),
            },
        )
        self.assertStatusOk(resp)
        uploadId = resp.json['_id']

        # Upload the contents of README.md
        resp = self.request(
            path='/file/chunk',
            method='POST',
            user=self.admin,
            body=self.readmeMarkdown,
            params={'uploadId': uploadId},
            type='text/plain',
        )
        self.assertStatusOk(resp)
        self.assertIn('itemId', resp.json)

        # Verify that the readme endpoint returns the correct response for admin
        resp = self.request(
            path=f'/folder/{self.privateFolder["_id"]}/readme',
            method='GET',
            user=self.admin,
            isJson=False,
        )
        self.assertStatusOk(resp)
        readme = b''
        for b in resp.body:
            readme += b
        assert self.readmeMarkdown == readme

        # Verify that the readme endpoint returns 403 Forbidden for user
        resp = self.request(
            path=f'/folder/{self.privateFolder["_id"]}/readme',
            method='GET',
            user=self.user,
            isJson=False,
        )
        self.assertStatus(resp, 403)

    def testNoReadme(self):
        # Verify that the readme endpoint returns 204 No Content when there is no README
        resp = self.request(
            path=f'/folder/{self.privateFolder["_id"]}/readme',
            method='GET',
            user=self.admin,
            isJson=False,
        )
        self.assertStatus(resp, 204)
