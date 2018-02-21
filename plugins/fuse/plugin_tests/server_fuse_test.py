#!/usr/bin/env python
# -*- coding: utf-8 -*-

import datetime
import fuse
import mock
import os
import six
import stat
import tempfile
import time

import girder
from girder import config
from girder.constants import AccessType
from girder.models.file import File
from girder.models.user import User
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
    retries = 0
    while retries < 50:
        try:
            os.rmdir(tempdir)
            break
        except OSError:
            retries += 1
            time.sleep(0.1)


class ServerFuseTestCase(base.TestCase):
    def setUp(self):
        super(ServerFuseTestCase, self).setUp()
        self.admin = User().findOne({'login': 'admin'})
        self.user = User().findOne({'login': 'user'})
        self.user2 = User().findOne({'login': 'second'})
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
        retries = 0
        while retries < 100:
            try:
                os.rmdir(self.extraMountPath)
                break
            except OSError:
                retries += 1
                time.sleep(0.1)

    def testMainMount(self):
        """
        Test the default mount point has access to all of the expected files.
        """
        mountpath = self.mainMountPath
        # Check that the mount lists users and collections
        self.assertEqual(sorted(os.listdir(mountpath)), sorted(['user', 'collection']))
        # Check that all known paths exist and that arbitrary other paths don't
        for testpath, contents in six.iteritems(self.knownPaths):
            localpath = os.path.join(mountpath, testpath)
            # The path must exist
            self.assertTrue(os.path.exists(localpath))
            # The path plus an arbitrary string must not exist
            self.assertFalse(os.path.exists(localpath + '.other'))
            # If the path is a file, check that it equals the expected value
            # and reports a non-zero size
            if contents:
                size = os.path.getsize(localpath)
                with open(localpath) as file1:
                    self.assertEqual(file1.read().strip(), contents)
                self.assertGreater(size, 0)
            # The mtime should be recent
            stat = os.stat(localpath)
            self.assertGreater(stat.st_mtime, time.time() - 1e5)
            # All parents should be folders and have zero size.
            subpath = testpath
            while '/' in subpath:
                subpath = subpath.rsplit('/')[0]
                localpath = os.path.join(mountpath, subpath)
                self.assertTrue(os.path.isdir(localpath))
                self.assertEqual(os.path.getsize(localpath), 0)
                # An arbitrary alternate file shjould not exist
                self.assertFalse(os.path.exists(localpath + '.other'))

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
        # The admin's private are not visible
        nonVisiblePattern = '/admin/Private'

        # Check that the mount lists users and collections
        self.assertEqual(sorted(os.listdir(mountpath)), sorted(['user', 'collection']))
        # Check that all known paths exist and that arbitrary other paths don't
        for testpath, contents in six.iteritems(self.knownPaths):
            localpath = os.path.join(mountpath, testpath)
            # We can see all path that aren't the admin's private paths
            canSee = nonVisiblePattern not in testpath
            self.assertEqual(os.path.exists(localpath), canSee)
            # If the path is a file and we can see it, check that it equals the
            # expected value, and raises an error if we can't see it.
            if contents:
                if canSee:
                    with open(localpath) as file1:
                        self.assertEqual(file1.read().strip(), contents)
                else:
                    with self.assertRaises(IOError):
                        with open(localpath) as file1:
                            pass
            # All parents should be folders if they can seen and report at not
            # if they can't.
            subpath = testpath
            while '/' in subpath:
                subpath = subpath.rsplit('/')[0]
                localpath = os.path.join(mountpath, subpath)
                canSee = nonVisiblePattern not in subpath
                self.assertEqual(os.path.isdir(localpath), canSee)

    def testSecondUserMount(self):
        """
        The second non-admin user should only see public items and folders.
        """
        from girder.plugins.fuse import server_fuse

        mountpath = self.extraMountPath
        self.extraMount = 'second'
        self.assertTrue(server_fuse.mountServerFuse(
            self.extraMount, mountpath, level=AccessType.READ, user=self.user2))
        # The OS can cache stat, so wait 1 second before using the mount.
        time.sleep(1)
        # Neither the admin's nor the user's private paths are visible
        nonVisiblePattern = '/Private'

        # Check that the mount lists users and collections
        self.assertEqual(sorted(os.listdir(mountpath)), sorted(['user', 'collection']))
        # Check that all known paths exist and that arbitrary other paths don't
        for testpath, contents in six.iteritems(self.knownPaths):
            localpath = os.path.join(mountpath, testpath)
            # We can see all path that aren't the admin's private paths
            canSee = nonVisiblePattern not in testpath
            self.assertEqual(os.path.exists(localpath), canSee)
            # If the path is a file and we can see it, check that it equals the
            # expected value, and raises an error if we can't see it.
            if contents:
                if canSee:
                    with open(localpath) as file1:
                        self.assertEqual(file1.read().strip(), contents)
                else:
                    with self.assertRaises(IOError):
                        with open(localpath) as file1:
                            pass
            # All parents should be folders if they can seen and report at not
            # if they can't.
            subpath = testpath
            while '/' in subpath:
                subpath = subpath.rsplit('/')[0]
                localpath = os.path.join(mountpath, subpath)
                canSee = nonVisiblePattern not in subpath
                self.assertEqual(os.path.isdir(localpath), canSee)

    def testFilePath(self):
        """
        Test that all files report a FUSE path, and that this results in the
        same file as the non-fuse path.
        """
        from girder.plugins import fuse as girder_fuse

        files = list(File().find())
        for file in files:
            adapter = File().getAssetstoreAdapter(file)
            filesystempath = adapter.fullPath(file)
            filepath = girder_fuse.getFilePath(file)
            fusepath = girder_fuse.getFuseFilePath(file)
            self.assertTrue(os.path.exists(filesystempath))
            self.assertTrue(os.path.exists(filepath))
            self.assertTrue(os.path.exists(fusepath))
            self.assertEqual(filesystempath, filepath)
            self.assertNotEqual(filesystempath, fusepath)
            self.assertEqual(fusepath[:len(self.mainMountPath)], self.mainMountPath)
            with open(filepath) as file1:
                with open(fusepath) as file2:
                    self.assertEqual(file1.read(), file2.read())
            subpath = fusepath[len(self.mainMountPath):].lstrip('/')
            if self.knownPaths.get(subpath):
                with open(fusepath) as file1:
                    self.assertEqual(file1.read().strip(), self.knownPaths[subpath])

    def testFilePathNoFullPath(self):
        """
        Test that if an assetstore adapter doesn't respond to fullPath, we
        always get the fuse path.
        """
        from girder.plugins import fuse as girder_fuse
        from girder.utility.filesystem_assetstore_adapter import FilesystemAssetstoreAdapter

        file = File().findOne()

        origFullPath = FilesystemAssetstoreAdapter.fullPath
        FilesystemAssetstoreAdapter.fullPath = None
        filepath = girder_fuse.getFilePath(file)
        fusepath = girder_fuse.getFuseFilePath(file)
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
        self.assertFalse(server_fuse.isServerFuseMounted(
            self.extraMount, level=AccessType.READ, user=self.user))
        self.assertTrue(server_fuse.mountServerFuse(
            self.extraMount, mountpath, level=AccessType.READ, user=self.user))
        # The OS can cache stat, so wait 1 second before using the mount.
        time.sleep(1)
        self.assertTrue(os.path.exists(publicFile))
        self.assertTrue(os.path.exists(privateFile))

    def testRemountWithoutChanges(self):
        """
        Test remounting with different credentials.
        """
        from girder.plugins.fuse import server_fuse

        mountpath = self.extraMountPath
        self.extraMount = 'remountWithoutChanges'
        # remount with user
        server_fuse.mountServerFuse(
            self.extraMount, mountpath, level=AccessType.READ, user=self.user)
        # remount without any changes should work
        self.assertTrue(server_fuse.isServerFuseMounted(
            self.extraMount, level=AccessType.READ, user=self.user))
        self.assertEqual(server_fuse.mountServerFuse(
            self.extraMount, mountpath, level=AccessType.READ, user=self.user),
            'present')

    def testStartFromConfig(self):
        from girder.plugins import fuse as girder_fuse

        girder.logger.error = mock.Mock(wraps=girder.logger.error)
        curConfig = config.getConfig()
        origdir = curConfig['server_fuse']['path']
        curConfig['server_fuse']['path'] = '/dev/null/nosuchpath'
        self.assertFalse(girder_fuse.startFromConfig())
        self.assertEqual(girder.logger.error.call_count, 1)
        self.assertIn('Can\'t mount resource fuse:', tuple(girder.logger.error.call_args)[0][0])
        fh, temppath = tempfile.mkstemp()
        os.write(fh, b'contents')
        curConfig['server_fuse']['path'] = temppath
        self.assertFalse(girder_fuse.startFromConfig())
        self.assertEqual(girder.logger.error.call_count, 2)
        self.assertIn('Can\'t mount resource fuse:', tuple(girder.logger.error.call_args)[0][0])
        os.close(fh)
        os.unlink(temppath)
        curConfig['server_fuse']['path'] = origdir

    def testGetServerFusePath(self):
        from girder.plugins import fuse as girder_fuse
        from girder.plugins.fuse import MAIN_FUSE_KEY, server_fuse

        file = File().findOne()
        fusepath = girder_fuse.getFuseFilePath(file)
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
        File().save(resource['document'])
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
        filelist = op._list(resource['document'], resource['model'])
        self.assertIn(os.path.basename(self.publicFileName), filelist)
        resource2 = op._getPath(os.path.dirname(os.path.dirname(self.publicFileName)))
        filelist = op._list(resource2['document'], resource2['model'])
        self.assertIn(os.path.basename(os.path.dirname(self.publicFileName)), filelist)
        resource3 = op._getPath(os.path.dirname(self.adminFileName))
        filelist = op._list(resource3['document'], resource3['model'])
        self.assertIn(os.path.basename(self.adminFileName), filelist)
        resource4 = op._getPath(os.path.dirname(os.path.dirname(self.adminFileName)))
        filelist = op._list(resource4['document'], resource4['model'])
        self.assertIn(os.path.basename(os.path.dirname(self.adminFileName)), filelist)
        resource5 = op._getPath(os.path.dirname(os.path.dirname(
            os.path.dirname(self.adminFileName))))
        filelist = op._list(resource5['document'], resource5['model'])
        self.assertIn(os.path.basename(os.path.dirname(
            os.path.dirname(self.adminFileName))), filelist)

        op = server_fuse.ServerFuse(user=self.user, force=False)
        resource6 = op._getPath(os.path.dirname(self.publicFileName))
        filelist = op._list(resource6['document'], resource6['model'])
        self.assertIn(os.path.basename(self.publicFileName), filelist)
        resource7 = op._getPath(os.path.dirname(os.path.dirname(self.publicFileName)))
        filelist = op._list(resource7['document'], resource7['model'])
        self.assertIn(os.path.basename(os.path.dirname(self.publicFileName)), filelist)
        # If we somehow have a document that we aren't authorized for, it can
        # still list files and items, but not folders.
        filelist = op._list(resource3['document'], resource3['model'])
        self.assertIn(os.path.basename(self.adminFileName), filelist)
        filelist = op._list(resource4['document'], resource4['model'])
        self.assertIn(os.path.basename(os.path.dirname(self.adminFileName)), filelist)
        filelist = op._list(resource5['document'], resource5['model'])
        self.assertNotIn(os.path.basename(os.path.dirname(
            os.path.dirname(self.adminFileName))), filelist)

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
        if (isinstance(data, six.binary_type) and
                not isinstance(self.knownPaths[self.publicFileName], six.binary_type)):
            self.assertEqual(data.decode('utf8').strip(), self.knownPaths[self.publicFileName])
        else:
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
