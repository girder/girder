#!/usr/bin/env python
# -*- coding: utf-8 -*-

#############################################################################
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
#############################################################################

import datetime
import fuse
import os
import stat
import tempfile
import time

from girder import config
from girder.constants import AccessType
from tests import base


def setUpModule():
    curConfig = config.getConfig()
    curConfig.setdefault('server_fuse', {})
    curConfig['server_fuse']['path'] = tempfile.mkdtemp()
    base.enabledPlugins.append('fuse')
    base.startServer()


def tearDownModule():
    curConfig = config.getConfig()
    tempdir = curConfig['server_fuse']['path']
    base.stopServer()
    os.rmdir(tempdir)


class ServerFuseTestCase(base.TestCase):
    def setUp(self):
        super(ServerFuseTestCase, self).setUp()
        self.admin = self.model('user').findOne({'login': 'admin'})
        self.user = self.model('user').findOne({'login': 'user'})
        self.user2 = self.model('user').findOne({'login': 'second'})
        curConfig = config.getConfig()
        self.mainMountPath = curConfig['server_fuse']['path']
        self.extraMountPath = tempfile.mkdtemp()
        self.extraMount = None
        self.knownPaths = {
            'user/admin/Private/Item 1/File 1A': 'File 1A',
            'user/admin/Private/Item 1/File 1B': 'File 1B',
            'user/admin/Private/Item 2/File 2': 'File 2',
            'user/admin/Private/Item Without File/': None,
            'user/user/Public/Item 3/File 3': 'File 3',
            'user/user/Private/Item 4/File 4': 'File 4',
            'user/user/Private/Folder/Item 5/File 5': 'File 5',
            'collection/Test Collection/Private/Collection Item/Collection File': 'File 1A',
        }
        self.adminFileName = 'user/admin/Private/Item 1/File 1A'
        self.publicFileName = 'user/user/Public/Item 3/File 3'
        self.privateFileName = 'user/user/Private/Item 4/File 4'

    def tearDown(self):
        from girder.plugins.fuse import server_fuse

        super(ServerFuseTestCase, self).tearDown()
        if self.extraMount:
            server_fuse.unmountServerFuse(self.extraMount)
        os.rmdir(self.extraMountPath)

    def testMainMount(self):
        """
        Test the default mount point has access to all of the expected files.
        """
        mountpath = self.mainMountPath
        self.assertEqual(sorted(os.listdir(mountpath)), sorted(['user', 'collection']))
        # Check that all known paths exist and that arbitrary other paths don't
        for fullpath in self.knownPaths:
            self.assertTrue(os.path.exists(os.path.join(mountpath, fullpath)))
            self.assertFalse(os.path.exists(os.path.join(mountpath, fullpath + '.other')))
            size = os.path.getsize(os.path.join(mountpath, fullpath))
            if self.knownPaths[fullpath]:
                self.assertEqual(
                    open(os.path.join(mountpath, fullpath)).read().strip(),
                    self.knownPaths[fullpath])
                self.assertGreater(size, 0)
            stat = os.stat(os.path.join(mountpath, fullpath))
            # The mtime should be recent
            self.assertGreater(stat.st_mtime, time.time() - 1e5)
            path = fullpath
            # All parents should be folders and have zero size.
            while '/' in path:
                path = path.rsplit('/')[0]
                self.assertTrue(os.path.isdir(os.path.join(mountpath, path)))
                self.assertFalse(os.path.exists(os.path.join(mountpath, path + '.other')))
                if '/' in path:
                    self.assertEqual(os.path.getsize(os.path.join(mountpath, path)), 0)

    def testUserMount(self):
        """
        The first non-admin user should be able to see all of their own items,
        folders, collections, and files, but not the admin items or private
        folders.
        """
        from girder.plugins.fuse import server_fuse

        mountpath = self.extraMountPath
        self.extraMount = 'test'
        self.assertTrue(server_fuse.mountServerFuse(
            self.extraMount, mountpath, level=AccessType.READ, user=self.user))
        # The OS can cache stat, so wait 1 second before using the mount.
        time.sleep(1)
        self.assertEqual(sorted(os.listdir(mountpath)), sorted(['user', 'collection']))
        for fullpath in self.knownPaths:
            canSee = not fullpath.startswith('user/admin')
            self.assertEqual(os.path.exists(os.path.join(mountpath, fullpath)), canSee)
            if canSee and self.knownPaths[fullpath]:
                self.assertEqual(
                    open(os.path.join(mountpath, fullpath)).read().strip(),
                    self.knownPaths[fullpath])
            elif self.knownPaths[fullpath]:
                with self.assertRaises(IOError):
                    open(os.path.join(mountpath, fullpath))
            path = fullpath
            # All parents should be folders and have zero size.
            while '/' in path:
                path = path.rsplit('/')[0]
                self.assertEqual(os.path.isdir(os.path.join(mountpath, path)),
                                 canSee or 'user/admin/Private' not in path)

    def testSecondUserMount(self):
        """
        The second non-admin user should only see publick items and folders.
        """
        from girder.plugins.fuse import server_fuse

        mountpath = self.extraMountPath
        self.extraMount = 'second'
        self.assertTrue(server_fuse.mountServerFuse(
            self.extraMount, mountpath, level=AccessType.READ, user=self.user2))
        # The OS can cache stat, so wait 1 second before using the mount.
        time.sleep(1)
        self.assertEqual(sorted(os.listdir(mountpath)), sorted(['user', 'collection']))
        for fullpath in self.knownPaths:
            canSee = 'Public' in fullpath
            self.assertEqual(os.path.exists(os.path.join(mountpath, fullpath)), canSee)
            if canSee:
                self.assertEqual(
                    open(os.path.join(mountpath, fullpath)).read().strip(),
                    self.knownPaths[fullpath])
            elif self.knownPaths[fullpath]:
                with self.assertRaises(IOError):
                    open(os.path.join(mountpath, fullpath))
            path = fullpath
            # All parents should be folders and have zero size.
            while '/' in path:
                path = path.rsplit('/')[0]
                self.assertEqual(os.path.isdir(os.path.join(mountpath, path)),
                                 'Private' not in path)

    def testFilePath(self):
        """
        Test that all files report a FUSE path, and that this results in the
        same file as the non-fuse path.
        """
        files = list(self.model('file').find())
        for file in files:
            adapter = self.model('file').getAssetstoreAdapter(file)
            filesystempath = adapter.fullPath(file)
            filepath = self.model('file').getFilePath(file)
            fusepath = self.model('file').getFuseFilePath(file)
            self.assertTrue(os.path.exists(filesystempath))
            self.assertTrue(os.path.exists(filepath))
            self.assertTrue(os.path.exists(fusepath))
            self.assertEqual(filesystempath, filepath)
            self.assertNotEqual(filesystempath, fusepath)
            self.assertEqual(fusepath[:len(self.mainMountPath)], self.mainMountPath)
            self.assertEqual(open(filepath).read(), open(fusepath).read())
            subpath = fusepath[len(self.mainMountPath):].lstrip('/')
            if self.knownPaths.get(subpath):
                self.assertEqual(open(fusepath).read().strip(), self.knownPaths[subpath])

    def testFilePathNoFullPath(self):
        """
        Test that if an assetstore adapter doesn't respond to fullPath, we
        always get the fuse path.
        """
        from girder.utility.filesystem_assetstore_adapter import FilesystemAssetstoreAdapter

        file = self.model('file').findOne()

        origFullPath = FilesystemAssetstoreAdapter.fullPath
        FilesystemAssetstoreAdapter.fullPath = None
        filepath = self.model('file').getFilePath(file)
        fusepath = self.model('file').getFuseFilePath(file)
        FilesystemAssetstoreAdapter.fullPath = origFullPath
        self.assertTrue(os.path.exists(filepath))
        self.assertTrue(os.path.exists(fusepath))
        self.assertEqual(filepath, fusepath)

    def testRemount(self):
        """
        Test remounting with different credentials.
        """
        from girder.plugins.fuse import server_fuse

        mountpath = self.extraMountPath
        self.extraMount = 'remount'
        # mount with user2
        self.assertTrue(server_fuse.mountServerFuse(
            self.extraMount, mountpath, level=AccessType.READ, user=self.user2))
        # The OS can cache stat, so wait 1 second before using the mount.
        time.sleep(1)
        publicFile = os.path.join(mountpath, self.publicFileName)
        privateFile = os.path.join(mountpath, self.privateFileName)
        self.assertTrue(os.path.exists(publicFile))
        self.assertFalse(os.path.exists(privateFile))
        # remount with user
        self.assertTrue(server_fuse.mountServerFuse(
            self.extraMount, mountpath, level=AccessType.READ, user=self.user))
        # The OS can cache stat, so wait 1 second before using the mount.
        time.sleep(1)
        self.assertTrue(os.path.exists(publicFile))
        self.assertTrue(os.path.exists(privateFile))
        # remount without any changes should work, too.
        self.assertEqual(server_fuse.mountServerFuse(
            self.extraMount, mountpath, level=AccessType.READ, user=self.user),
            'present')

    def testStartFromConfig(self):
        from girder.plugins import fuse as girder_fuse

        curConfig = config.getConfig()
        origdir = curConfig['server_fuse']['path']
        curConfig['server_fuse']['path'] = '/dev/null/nosuchpath'
        self.assertFalse(girder_fuse.startFromConfig())
        fh, temppath = tempfile.mkstemp()
        os.write(fh, 'contents')
        curConfig['server_fuse']['path'] = temppath
        self.assertFalse(girder_fuse.startFromConfig())
        os.unlink(temppath)
        curConfig['server_fuse']['path'] = origdir

    def testGetServerFusePath(self):
        from girder.plugins.fuse import MAIN_FUSE_KEY, server_fuse

        file = self.model('file').findOne()
        fusepath = self.model('file').getFuseFilePath(file)
        sfpath = server_fuse.getServerFusePath(MAIN_FUSE_KEY, 'file', file)
        self.assertEqual(fusepath, sfpath)
        self.assertIsNone(server_fuse.getServerFusePath('unknown', 'file', file))

    # Although other tests excerise the individual functions in the FUSE,
    # coverage is not reported since it is run in a separate process.  Each of
    # the operation class functions is tested here.

    def testFunctionCall(self):
        from girder.plugins.fuse import server_fuse

        op = server_fuse.ServerFuse(user=self.user2, force=False)
        self.assertEqual(op.__call__('access', self.publicFileName, os.F_OK), 0)
        with self.assertRaises(fuse.FuseOSError):
            op.__call__('access', self.privateFileName, os.F_OK)
        with self.assertRaises(fuse.FuseOSError):
            op.__call__('access', 'nosuchpath', os.F_OK)
        with self.assertRaises(fuse.FuseOSError):
            self.assertTrue(op.__call__('read', self.publicFileName, 10, 0, None))

    def testFunctionGetPath(self):
        from girder.plugins.fuse import server_fuse

        op = server_fuse.ServerFuse(user=self.user2, force=False)
        resource = op._getPath(self.publicFileName)
        self.assertEqual(resource['model'], 'file')
        resource = op._getPath(os.path.dirname(self.publicFileName))
        self.assertEqual(resource['model'], 'item')
        resource = op._getPath(os.path.dirname(os.path.dirname(self.publicFileName)))
        self.assertEqual(resource['model'], 'folder')
        with self.assertRaises(fuse.FuseOSError):
            op._getPath(self.privateFileName)
        with self.assertRaises(fuse.FuseOSError):
            op._getPath('nosuchpath')

    def testFunctionStat(self):
        from girder.plugins.fuse import server_fuse

        op = server_fuse.ServerFuse(user=self.user2, force=False)
        resource = op._getPath(self.publicFileName)
        attr = op._stat(resource['document'], resource['model'])
        self.assertEqual(attr['st_ino'], -1)
        self.assertEqual(attr['st_nlink'], 1)
        self.assertGreater(attr['st_mtime'], time.time() - 1e5)
        self.assertEqual(attr['st_ctime'], attr['st_mtime'])
        self.assertEqual(attr['st_mode'], 0o400 | stat.S_IFREG)
        self.assertGreater(attr['st_size'], len(self.knownPaths[self.publicFileName]))
        resource['document']['updated'] = datetime.datetime.utcfromtimestamp(time.time() + 1)
        self.model('file').save(resource['document'])
        oldmtime = attr['st_mtime']
        resource = op._getPath(self.publicFileName)
        attr = op._stat(resource['document'], resource['model'])
        self.assertGreater(attr['st_mtime'], oldmtime)

        resource = op._getPath(os.path.dirname(self.publicFileName))
        attr = op._stat(resource['document'], resource['model'])
        self.assertEqual(attr['st_mode'], 0o500 | stat.S_IFDIR)
        self.assertEqual(attr['st_size'], 0)
        resource = op._getPath(os.path.dirname(os.path.dirname(self.publicFileName)))
        attr = op._stat(resource['document'], resource['model'])
        self.assertEqual(attr['st_mode'], 0o500 | stat.S_IFDIR)
        self.assertEqual(attr['st_size'], 0)

    def testFunctionName(self):
        from girder.plugins.fuse import server_fuse

        op = server_fuse.ServerFuse(user=self.user2, force=False)
        resource = op._getPath(self.publicFileName)
        name = op._name(resource['document'], resource['model'])
        self.assertEqual(name, os.path.basename(self.publicFileName))
        resource = op._getPath(os.path.dirname(self.publicFileName))
        name = op._name(resource['document'], resource['model'])
        self.assertEqual(name, os.path.basename(os.path.dirname(self.publicFileName)))

    def testFunctionList(self):
        from girder.plugins.fuse import server_fuse

        op = server_fuse.ServerFuse()
        resource = op._getPath(os.path.dirname(self.publicFileName))
        list = op._list(resource['document'], resource['model'])
        self.assertIn(os.path.basename(self.publicFileName), list)
        resource2 = op._getPath(os.path.dirname(os.path.dirname(self.publicFileName)))
        list = op._list(resource2['document'], resource2['model'])
        self.assertIn(os.path.basename(os.path.dirname(self.publicFileName)), list)
        resource3 = op._getPath(os.path.dirname(self.adminFileName))
        list = op._list(resource3['document'], resource3['model'])
        self.assertIn(os.path.basename(self.adminFileName), list)
        resource4 = op._getPath(os.path.dirname(os.path.dirname(self.adminFileName)))
        list = op._list(resource4['document'], resource4['model'])
        self.assertIn(os.path.basename(os.path.dirname(self.adminFileName)), list)
        resource5 = op._getPath(os.path.dirname(os.path.dirname(
            os.path.dirname(self.adminFileName))))
        list = op._list(resource5['document'], resource5['model'])
        self.assertIn(os.path.basename(os.path.dirname(
            os.path.dirname(self.adminFileName))), list)

        op = server_fuse.ServerFuse(user=self.user, force=False)
        resource6 = op._getPath(os.path.dirname(self.publicFileName))
        list = op._list(resource6['document'], resource6['model'])
        self.assertIn(os.path.basename(self.publicFileName), list)
        resource7 = op._getPath(os.path.dirname(os.path.dirname(self.publicFileName)))
        list = op._list(resource7['document'], resource7['model'])
        self.assertIn(os.path.basename(os.path.dirname(self.publicFileName)), list)
        # If we somehow have a document that we aren't authorized for, it can
        # still list files and items, but not folders.
        list = op._list(resource3['document'], resource3['model'])
        self.assertIn(os.path.basename(self.adminFileName), list)
        list = op._list(resource4['document'], resource4['model'])
        self.assertIn(os.path.basename(os.path.dirname(self.adminFileName)), list)
        list = op._list(resource5['document'], resource5['model'])
        self.assertNotIn(os.path.basename(os.path.dirname(
            os.path.dirname(self.adminFileName))), list)

    def testFunctionAccess(self):
        from girder.plugins.fuse import server_fuse

        op = server_fuse.ServerFuse()
        self.assertEqual(op.access(self.publicFileName, os.F_OK), 0)
        self.assertEqual(op.access(self.publicFileName, os.R_OK | os.W_OK | os.X_OK), 0)
        self.assertEqual(op.access(self.adminFileName, os.F_OK), 0)
        self.assertEqual(op.access(self.adminFileName, os.R_OK), 0)
        op = server_fuse.ServerFuse(user=self.user, force=False)
        self.assertEqual(op.access(self.publicFileName, os.F_OK), 0)
        self.assertEqual(op.access(self.publicFileName, os.R_OK | os.W_OK | os.X_OK), 0)
        with self.assertRaises(fuse.FuseOSError):
            op.access(self.adminFileName, os.F_OK)
        with self.assertRaises(fuse.FuseOSError):
            op.access(self.adminFileName, os.R_OK)

    def testFunctionGetattr(self):
        from girder.plugins.fuse import server_fuse

        op = server_fuse.ServerFuse()
        attr = op.getattr('/user')
        self.assertEqual(attr['st_mode'], 0o500 | stat.S_IFDIR)
        self.assertEqual(attr['st_size'], 0)
        attr = op.getattr(self.publicFileName)
        self.assertEqual(attr['st_ino'], -1)
        self.assertEqual(attr['st_nlink'], 1)
        self.assertGreater(attr['st_mtime'], time.time() - 1e5)
        self.assertEqual(attr['st_ctime'], attr['st_mtime'])
        self.assertEqual(attr['st_mode'], 0o400 | stat.S_IFREG)
        self.assertGreater(attr['st_size'], len(self.knownPaths[self.publicFileName]))

    def testFunctionRead(self):
        from girder.plugins.fuse import server_fuse

        op = server_fuse.ServerFuse()
        fh = op.open(self.publicFileName, os.O_RDONLY)
        data = op.read(self.publicFileName, 200, 0, fh)
        self.assertEqual(data.strip(), self.knownPaths[self.publicFileName])
        data2 = op.read(self.publicFileName, 4, 2, fh)
        self.assertEqual(data[2:6], data2)
        op.release(self.publicFileName, fh)
        with self.assertRaises(fuse.FuseOSError):
            op.read(self.publicFileName, 4, 2, fh)

    def testFunctionReaddir(self):
        from girder.plugins.fuse import server_fuse
        path = os.path.dirname(self.publicFileName)

        op = server_fuse.ServerFuse()
        data = op.readdir(path, 0)
        self.assertIn(os.path.basename(self.publicFileName), data)
        data = op.readdir('/user', 0)
        self.assertIn('admin', data)
        data = op.readdir('', 0)
        self.assertIn('user', data)
        self.assertIn('collection', data)
        self.assertIn('.', data)
        self.assertIn('..', data)
        data = op.readdir('/collection', 0)
        self.assertEqual(len(data), 3)

        op = server_fuse.ServerFuse(user=self.user2, force=False)
        data = op.readdir(path, 0)
        self.assertIn(os.path.basename(self.publicFileName), data)
        data = op.readdir('/user', 0)
        self.assertIn('admin', data)
        data = op.readdir('/collection', 0)
        self.assertEqual(len(data), 3)

    def testFunctionOpen(self):
        from girder.plugins.fuse import server_fuse
        op = server_fuse.ServerFuse()

        fh = op.open(self.publicFileName, os.O_RDONLY)
        self.assertTrue(isinstance(fh, int))
        self.assertIn(fh, op.openFiles)
        path = os.path.dirname(self.publicFileName)
        fh = op.open(path, os.O_RDONLY)
        self.assertTrue(isinstance(fh, int))
        self.assertNotIn(fh, op.openFiles)
        for flag in (os.O_APPEND, os.O_ASYNC, os.O_CREAT, os.O_DIRECTORY,
                     os.O_EXCL, os.O_RDWR, os.O_TRUNC, os.O_WRONLY):
            with self.assertRaises(fuse.FuseOSError):
                op.open(self.publicFileName, flag)

    def testFunctionCreate(self):
        from girder.plugins.fuse import server_fuse
        op = server_fuse.ServerFuse()

        with self.assertRaises(fuse.FuseOSError):
            op.create(self.publicFileName, 0)

    def testFunctionRelease(self):
        from girder.plugins.fuse import server_fuse
        op = server_fuse.ServerFuse()

        fh = op.open(self.publicFileName, os.O_RDONLY)
        self.assertIn(fh, op.openFiles)
        self.assertEqual(op.release(self.publicFileName, fh), 0)
        self.assertNotIn(fh, op.openFiles)
        path = os.path.dirname(self.publicFileName)
        fh = op.open(path, os.O_RDONLY)
        self.assertNotIn(fh, op.openFiles)
        self.assertEqual(op.release(path, fh), 0)

    def testFunctionDestroy(self):
        from girder.plugins.fuse import server_fuse
        op = server_fuse.ServerFuse()

        self.assertIsNone(op.destroy('/'))
