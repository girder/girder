# -*- coding: utf-8 -*-
import os
import subprocess
import tempfile
import time

from girder.constants import ROOT_DIR
from girder.exceptions import FilePathException
from girder.models.file import File
from girder.models.folder import Folder
from girder.models.item import Item
from girder.models.user import User

from .. import base


def setUpModule():
    base.startServer()


def tearDownModule():
    base.stopServer()


class MountCommandTestCase(base.TestCase):
    def setUp(self):
        super().setUp()
        info = {
            'email': 'admin@girder.test',
            'login': 'admin',
            'firstName': 'Admin',
            'lastName': 'Admin',
            'password': 'adminpassword',
            'admin': True
        }
        self.admin = User().createUser(**info)
        self.publicFolder = next(Folder().childFolders(
            self.admin, parentType='user', force=True, filters={'name': 'Public'}))
        self.item = Item().createItem('test', self.admin, self.publicFolder)
        path = os.path.join(
            ROOT_DIR, 'tests', 'cases', 'mount_test_files', 'file1a.txt')
        file = File().createFile(
            name='file1a.txt', creator=self.admin, item=self.item,
            assetstore=self.assetstore, size=os.path.getsize(path))
        file['imported'] = True
        file['path'] = path
        self.file = File().save(file)

    def testMountCommand(self):
        """
        Use the mount command to mount a FUSE file system  Check that we can
        read a file from there and that it unmounts.
        """
        with self.assertRaises(FilePathException):
            File().getGirderMountFilePath(self.file)
        self.assertIsNone(File().getGirderMountFilePath(self.file, validate=False))
        mountPath = tempfile.mkdtemp()
        subprocess.check_call(['girder', 'mount', mountPath, '-d', os.environ['GIRDER_TEST_DB']])
        endTime = time.time() + 10  # maximum time to wait
        while time.time() < endTime:
            if os.path.exists(os.path.join(mountPath, 'user')):
                break
            time.sleep(0.1)
        filePath = os.path.join(mountPath, 'user', 'admin', 'Public', 'test', 'file1a.txt')
        self.assertEqual(File().getGirderMountFilePath(self.file), filePath)
        self.assertNotEqual(File().getGirderMountFilePath(self.file),
                            File().getLocalFilePath(self.file))
        self.assertTrue(os.path.exists(filePath))
        self.assertEqual(open(filePath).read().strip(), 'File 1A')
        subprocess.check_call(['girder', 'mount', mountPath, '-u'])
        endTime = time.time() + 10  # maximum time to wait
        while time.time() < endTime:
            if not os.path.exists(os.path.join(mountPath, 'user')):
                break
            time.sleep(0.1)
        self.assertFalse(os.path.exists(filePath))
        os.rmdir(mountPath)
        with self.assertRaises(FilePathException):
            File().getGirderMountFilePath(self.file)
