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

import paramiko
import six
import stat
import threading

from .. import base
from girder.api import sftp

server = None
TEST_PORT = 10551


def setUpModule():
    global server
    server = sftp.SftpServer(('localhost', TEST_PORT))
    serverThread = threading.Thread(target=server.serve_forever)
    serverThread.daemon = True
    serverThread.start()


def tearDownModule():
    if server:
        server.server_close()


class SftpTestCase(base.TestCase):
    def testSftpService(self):
        users = ({
            'email': 'admin@email.com',
            'login': 'admin',
            'firstName': 'First',
            'lastName': 'Last',
            'password': 'passwd'
        }, {
            'email': 'regularuser@email.com',
            'login': 'regularuser',
            'firstName': 'First',
            'lastName': 'Last',
            'password': 'passwd'
        })

        admin, user = [self.model('user').createUser(**user) for user in users]

        collections = ({
            'name': 'public collection',
            'public': True,
            'creator': admin
        }, {
            'name': 'private collection',
            'public': False,
            'creator': admin
        })

        privateFolder = self.model('folder').findOne({
            'parentCollection': 'user',
            'parentId': user['_id'],
            'name': 'Private'
        })
        self.assertIsNotNone(privateFolder)

        self.model('upload').uploadFromFile(
            six.BytesIO(b'hello world'), size=11, name='test.txt', parentType='folder',
            parent=privateFolder, user=user)

        for coll in collections:
            self.model('collection').createCollection(**coll)

        client = paramiko.SSHClient()
        client.load_system_host_keys()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        # Incorrect password should raise authentication error
        with self.assertRaises(paramiko.AuthenticationException):
            client.connect(
                'localhost', TEST_PORT, username='admin', password='badpass', look_for_keys=False)

        # Authenticate as admin
        client.connect(
            'localhost', TEST_PORT, username='admin', password='passwd', look_for_keys=False)
        sftpClient = client.open_sftp()
        self.assertEqual(sftpClient.listdir('/'), ['collection', 'user'])

        # Listing an invalid top level entity should fail
        with self.assertRaises(IOError):
            sftpClient.listdir('/foo')

        # Test listing of users, collections, and subfolders
        self.assertEqual(set(sftpClient.listdir('/user/')), {'admin', 'regularuser'})
        self.assertEqual(set(sftpClient.listdir('/user/admin')), {'Public', 'Private'})
        self.assertEqual(
            set(sftpClient.listdir('/collection')), {'public collection', 'private collection'})

        self.assertEqual(sftpClient.listdir('/user/regularuser/Private'), ['test.txt'])
        self.assertEqual(sftpClient.listdir('/user/regularuser/Private/test.txt'), ['test.txt'])

        with six.assertRaisesRegex(self, IOError, 'No such file'):
            sftpClient.listdir('/user/nonexistent')

        with six.assertRaisesRegex(self, IOError, 'No such file'):
            sftpClient.file('/user/regularuser/Private')

        # Read a file using small enough buf size to require multiple chunks internally.
        file = sftpClient.file('/user/regularuser/Private/test.txt/test.txt', 'r', bufsize=4)
        self.assertEqual(file.read(2), b'he')
        self.assertEqual(file.read(), b'llo world')

        # Test stat capability
        info = sftpClient.stat('/user/regularuser/Private')
        self.assertTrue(stat.S_ISDIR(info.st_mode))
        self.assertFalse(stat.S_ISREG(info.st_mode))
        self.assertEqual(info.st_mode & 0o777, 0o777)

        info = sftpClient.stat('/user/regularuser/Private/test.txt/test.txt')
        self.assertFalse(stat.S_ISDIR(info.st_mode))
        self.assertTrue(stat.S_ISREG(info.st_mode))
        self.assertEqual(info.st_size, 11)
        self.assertEqual(info.st_mode & 0o777, 0o777)

        # File stat implementations should agree
        info = file.stat()
        self.assertFalse(stat.S_ISDIR(info.st_mode))
        self.assertTrue(stat.S_ISREG(info.st_mode))
        self.assertEqual(info.st_size, 11)
        self.assertEqual(info.st_mode & 0o777, 0o777)

        sftpClient.close()
        client.close()

        # Test anonymous access
        client = paramiko.SSHClient()
        client.load_system_host_keys()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        client.connect(
            'localhost', TEST_PORT, username='anonymous', password='', look_for_keys=False)
        sftpClient = client.open_sftp()

        # Only public data should be visible
        self.assertEqual(set(sftpClient.listdir('/user')), {'admin', 'regularuser'})
        self.assertEqual(sftpClient.listdir('/collection'), ['public collection'])
        self.assertEqual(sftpClient.listdir('/user/admin'), ['Public'])

        # Make sure the client cannot distinguish between a resource that does not exist
        # vs. one they simply don't have read access to.
        with six.assertRaisesRegex(self, IOError, 'No such file'):
            sftpClient.listdir('/user/regularuser/Private')

        with six.assertRaisesRegex(self, IOError, 'No such file'):
            sftpClient.file('/user/regularuser/Private/test.txt/test.txt', 'r')

        sftpClient.close()
        client.close()
