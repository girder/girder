#!/usr/bin/env python
# -*- coding: utf-8 -*-

import datetime
import fuse
import mock
import os
import six
import stat
import tempfile
import threading
import time

from girder.cli import mount
from girder.constants import SettingKey
from girder.exceptions import ValidationException
from girder.models.file import File
from girder.models.setting import Setting
from girder.models.user import User
from tests import base


class ServerFuseTestCase(base.TestCase):
    def _mountServer(self, path, shouldSucceed=True, maxWait=10, options=None):
        """
        For testing, run the mount in the foreground in a thread.  If the mount
        should succeed, wait a short time for a mount to be ready.  In local
        testing, this can take 8 to 10 milliseconds.

        :param path: the mount path.  This waits for <path>/user to exist
        :param maxWait: the maximum wait time in seconds.
        :param options: fuseOptions to use in the mount.  This should include
            'foreground' for testing.
        """
        kwargs = {
            'fuseOptions': options or 'foreground',
            'quiet': True,
        }
        mountThread = threading.Thread(target=mount.mountServer, args=(path, ), kwargs=kwargs)
        mountThread.daemon = True
        mountThread.start()
        if shouldSucceed:
            userPath = os.path.join(path, 'user')
            endTime = time.time() + maxWait
            while time.time() < endTime and not os.path.exists(userPath):
                time.sleep(0.001)
            self._mountThreads.append(mountThread)
        else:
            mountThread.join()
        return mountThread

    def setUp(self):
        super(ServerFuseTestCase, self).setUp()
        self._mountThreads = []
        self.admin = User().findOne({'login': 'admin'})
        self.user = User().findOne({'login': 'user'})
        self.user2 = User().findOne({'login': 'second'})
        self.mountPath = tempfile.mkdtemp()
        self._mountServer(path=self.mountPath)
        self.extraMountPath = tempfile.mkdtemp()
        self.knownPaths = {
            'user/admin/Private/Item 1/File 1A': 'File 1A',
            'user/admin/Private/Item 1/File 1B': 'File 1B',
            'user/admin/Private/Item 2/File 2': 'File 2',
            'user/admin/Private/Item Without File/': None,
            'user/user/Public/Item 3/File 3': 'File 3',
            'user/user/Private/Item 4/File 4': 'File 4',
            'user/user/Private/Folder/Item 5/File 5': 'File 5',
            'collection/Test Collection/Private/Collection Item/Collection File': 'File 1A',
            u'collection/Test Collection/Private/Collection Item/'
            u'\u0444\u0430\u0439\u043b \u043a\u043e\u043b\u043b\u0435\u043a'
            u'\u0446\u0438\u0438': 'File 1A',
        }
        self.adminFileName = 'user/admin/Private/Item 1/File 1A'
        self.publicFileName = 'user/user/Public/Item 3/File 3'
        self.privateFileName = 'user/user/Private/Item 4/File 4'

    def tearDown(self):
        super(ServerFuseTestCase, self).tearDown()
        mount.unmountServer(self.mountPath, quiet=True)
        mount.unmountServer(self.extraMountPath, quiet=True)
        os.rmdir(self.mountPath)
        os.rmdir(self.extraMountPath)
        # Join threads that are done
        for thread in self._mountThreads:
            thread.join()
        self._mountThreads = []

    def testMainMount(self):
        """
        Test the default mount point has access to all of the expected files.
        """
        mountpath = self.mountPath
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
                # An arbitrary alternate file should not exist
                self.assertFalse(os.path.exists(localpath + '.other'))

    def testBlockedMount(self):
        """
        Test that when a mount point is non-empty the mount fails.
        """
        blockFile = os.path.join(self.extraMountPath, 'block')
        open(blockFile, 'wb').close()
        with mock.patch('girder.plugin.logprint.error') as logprint:
            self._mountServer(path=self.extraMountPath, shouldSucceed=False)
            logprint.assert_called_once()
        os.unlink(blockFile)

    def testRWMountWarns(self):
        """
        Test that when asking for an RW mount, a warning is issued.
        """
        with mock.patch('girder.plugin.logprint.warning') as logprint:
            self._mountServer(path=self.extraMountPath, options='foreground,rw=true')
            logprint.assert_called_once()
            logprint.assert_called_with('Ignoring the rw=True option')

    def testFilePath(self):
        """
        Test that all files report a FUSE path, and that this results in the
        same file as the non-fuse path.
        """
        files = list(File().find())
        for file in files:
            adapter = File().getAssetstoreAdapter(file)
            filesystempath = adapter.fullPath(file)
            filepath = File().getLocalFilePath(file)
            fusepath = File().getGirderMountFilePath(file)
            self.assertTrue(os.path.exists(filesystempath))
            self.assertTrue(os.path.exists(filepath))
            self.assertTrue(os.path.exists(fusepath))
            self.assertEqual(filesystempath, filepath)
            self.assertNotEqual(filesystempath, fusepath)
            self.assertEqual(fusepath[:len(self.mountPath)], self.mountPath)
            with open(filepath) as file1:
                with open(fusepath) as file2:
                    self.assertEqual(file1.read(), file2.read())
            subpath = fusepath[len(self.mountPath):].lstrip('/')
            if self.knownPaths.get(subpath):
                with open(fusepath) as file1:
                    self.assertEqual(file1.read().strip(), self.knownPaths[subpath])

    def testFilePathNoLocalPath(self):
        """
        Test that if an assetstore adapter doesn't respond to getLocalFilePath,
        we always get the fuse path.
        """
        from girder.utility.filesystem_assetstore_adapter import FilesystemAssetstoreAdapter

        def getLocalFilePath(self, file):
            return super(FilesystemAssetstoreAdapter, self).getLocalFilePath(file)

        file = File().findOne()

        origGetLocalFilePath = FilesystemAssetstoreAdapter.getLocalFilePath
        FilesystemAssetstoreAdapter.getLocalFilePath = getLocalFilePath
        filepath = File().getLocalFilePath(file)
        fusepath = File().getGirderMountFilePath(file)
        FilesystemAssetstoreAdapter.getLocalFilePath = origGetLocalFilePath
        self.assertTrue(os.path.exists(filepath))
        self.assertTrue(os.path.exists(fusepath))
        self.assertEqual(filepath, fusepath)

    def testRemountAndSetting(self):
        """
        Test remounting to a different location.
        """
        # Check that the setting for the mount location matches the current
        # mount and a file is reachable where we expect.
        setting = Setting().get(SettingKey.GIRDER_MOUNT_INFORMATION, None)
        self.assertEqual(setting['path'], self.mountPath)
        self.assertTrue(os.path.exists(os.path.join(self.mountPath, self.publicFileName)))
        self.assertFalse(os.path.exists(os.path.join(self.extraMountPath, self.publicFileName)))
        mount.unmountServer(self.mountPath)
        # After unmounting, the setting should be cleared (though perhaps not
        # instantly) and files shouldn't be reachable.
        endTime = time.time() + 10  # maximum time to wait
        while time.time() < endTime:
            setting = Setting().get(SettingKey.GIRDER_MOUNT_INFORMATION, None)
            if setting is None:
                break
            time.sleep(0.05)
        setting = Setting().get(SettingKey.GIRDER_MOUNT_INFORMATION, None)
        self.assertIsNone(setting)
        self.assertFalse(os.path.exists(os.path.join(self.mountPath, self.publicFileName)))
        self.assertFalse(os.path.exists(os.path.join(self.extraMountPath, self.publicFileName)))
        # Remounting to a different path should update the setting and make
        # files visible again.
        self._mountServer(path=self.extraMountPath)
        setting = Setting().get(SettingKey.GIRDER_MOUNT_INFORMATION, None)
        self.assertEqual(setting['path'], self.extraMountPath)
        self.assertFalse(os.path.exists(os.path.join(self.mountPath, self.publicFileName)))
        self.assertTrue(os.path.exists(os.path.join(self.extraMountPath, self.publicFileName)))

    def testUnmountWithOpenFiles(self):
        """
        Unmounting with open files will return a non-zero value.
        """
        path = os.path.join(self.mountPath, self.publicFileName)
        fh = open(path)
        fh.read(1)
        self.assertNotEqual(mount.unmountServer(self.mountPath, quiet=True), 0)
        # We should still be able to read from the file.
        fh.read(1)
        fh.close()
        # Now we can unmount successefully
        self.assertEqual(mount.unmountServer(self.mountPath, quiet=True), 0)

    def testLazyUnmountWithOpenFiles(self):
        """
        Lazy unmounting with open files will return a non-zero value.
        """
        path = os.path.join(self.mountPath, self.publicFileName)
        fh = open(path)
        fh.read(1)
        self.assertEqual(mount.unmountServer(self.mountPath, lazy=True, quiet=True), 0)
        # We should still be able to read from the file.
        fh.read(1)
        fh.close()
        # If we wait, the mount will close
        endTime = time.time() + 10  # maximum time to wait
        while time.time() < endTime:
            if not os.path.exists(path):
                break
            time.sleep(0.05)
        self.assertFalse(os.path.exists(path))

    def testSettingValidation(self):
        # Mounting and unmounting test valid use, so this just tests invalid
        # values.
        with six.assertRaisesRegex(self, ValidationException, 'must be a dict'):
            Setting().set(SettingKey.GIRDER_MOUNT_INFORMATION, 'not a dict')
        with six.assertRaisesRegex(self, ValidationException, 'with the "path" key'):
            Setting().set(SettingKey.GIRDER_MOUNT_INFORMATION, {'no path': 'key'})

    # Although other tests excerise the individual functions in the FUSE,
    # coverage is not reported since it is run in a separate process.  Each of
    # the operation class functions is tested here.

    def testFunctionCall(self):
        op = mount.ServerFuse()
        self.assertEqual(op.__call__('access', self.publicFileName, os.F_OK), 0)
        self.assertEqual(op.__call__('access', self.privateFileName, os.F_OK), 0)
        self.assertEqual(op.__call__('access', 'nosuchpath', os.F_OK), 0)
        with self.assertRaises(fuse.FuseOSError):
            self.assertTrue(op.__call__('read', self.publicFileName, 10, 0, None))

    def testFunctionGetPath(self):
        op = mount.ServerFuse()
        resource = op._getPath(self.publicFileName)
        self.assertEqual(resource['model'], 'file')
        resource = op._getPath(os.path.dirname(self.publicFileName))
        self.assertEqual(resource['model'], 'item')
        resource = op._getPath(os.path.dirname(os.path.dirname(self.publicFileName)))
        self.assertEqual(resource['model'], 'folder')
        resource = op._getPath(self.privateFileName)
        self.assertEqual(resource['model'], 'file')
        with self.assertRaises(fuse.FuseOSError):
            op._getPath('nosuchpath')

    def testFunctionStat(self):
        op = mount.ServerFuse()
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
        op = mount.ServerFuse()
        resource = op._getPath(self.publicFileName)
        name = op._name(resource['document'], resource['model'])
        self.assertEqual(name, os.path.basename(self.publicFileName))
        resource = op._getPath(os.path.dirname(self.publicFileName))
        name = op._name(resource['document'], resource['model'])
        self.assertEqual(name, os.path.basename(os.path.dirname(self.publicFileName)))

    def testFunctionList(self):
        op = mount.ServerFuse()
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

    def testFunctionAccess(self):
        op = mount.ServerFuse()
        self.assertEqual(op.access(self.publicFileName, os.F_OK), 0)
        self.assertEqual(op.access(self.publicFileName, os.R_OK | os.W_OK | os.X_OK), 0)
        self.assertEqual(op.access(self.adminFileName, os.F_OK), 0)
        self.assertEqual(op.access(self.adminFileName, os.R_OK), 0)
        self.assertEqual(op.access('/user', os.F_OK), 0)

    def testFunctionGetattr(self):
        op = mount.ServerFuse()
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
        with self.assertRaises(fuse.FuseOSError):
            op.getattr('/user/nosuchuser')

    def testFunctionRead(self):
        op = mount.ServerFuse()
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
        op = mount.ServerFuse()
        path = os.path.dirname(self.publicFileName)
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

    def testFunctionOpen(self):
        op = mount.ServerFuse()
        fh = op.open(self.publicFileName, os.O_RDONLY)
        self.assertTrue(isinstance(fh, int))
        self.assertIn(fh, op.openFiles)
        op.release(self.publicFileName, fh)
        path = os.path.dirname(self.publicFileName)
        fh = op.open(path, os.O_RDONLY)
        self.assertTrue(isinstance(fh, int))
        self.assertNotIn(fh, op.openFiles)
        for flag in (os.O_APPEND, os.O_ASYNC, os.O_CREAT, os.O_DIRECTORY,
                     os.O_EXCL, os.O_RDWR, os.O_TRUNC, os.O_WRONLY):
            with self.assertRaises(fuse.FuseOSError):
                op.open(self.publicFileName, flag)

    def testFunctionCreate(self):
        op = mount.ServerFuse()
        with self.assertRaises(fuse.FuseOSError):
            op.create(self.publicFileName, 0)

    def testFunctionFlush(self):
        op = mount.ServerFuse()
        self.assertEqual(op.flush('/user'), 0)

    def testFunctionRelease(self):
        op = mount.ServerFuse()

        fh = op.open(self.publicFileName, os.O_RDONLY)
        self.assertIn(fh, op.openFiles)
        self.assertEqual(op.release(self.publicFileName, fh), 0)
        self.assertNotIn(fh, op.openFiles)
        path = os.path.dirname(self.publicFileName)
        fh = op.open(path, os.O_RDONLY)
        self.assertNotIn(fh, op.openFiles)
        self.assertEqual(op.release(path, fh), 0)

    def testFunctionDestroy(self):
        op = mount.ServerFuse()
        self.assertIsNone(op.destroy('/'))
