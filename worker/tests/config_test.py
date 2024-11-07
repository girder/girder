from unittest import mock
import os
import girder_worker
import girder_worker.configure
import unittest
import sys
from configparser import ConfigParser, NoOptionError
from . import captureOutput

local_cfg = os.path.join(girder_worker.PACKAGE_DIR, 'worker.local.cfg')


class SysExitException(Exception):
    pass


def setUpModule():
    # Backup local config file if it exists
    if os.path.exists(local_cfg):
        os.rename(local_cfg, local_cfg + '.bak')
        # Re-read the configs
        girder_worker.config = ConfigParser()
        _cfgs = ('worker.dist.cfg', 'worker.local.cfg')
        girder_worker.config.read(
            [os.path.join(girder_worker.PACKAGE_DIR, f) for f in _cfgs])


def tearDownModule():
    # Restore local config from backup if it exists
    if os.path.exists(local_cfg + '.bak'):
        os.rename(local_cfg + '.bak', local_cfg)


class TestConfigScript(unittest.TestCase):
    def _runConfigScript(self, args):
        args = ['girder-worker-config'] + args
        rc = 0
        with mock.patch.object(sys, 'argv', args), \
                mock.patch('sys.exit', side_effect=SysExitException) as exit, \
                captureOutput() as output:
            try:
                girder_worker.configure.main()
            except SysExitException:
                args = exit.mock_calls[0][1]
                rc = args[0] if len(args) else 0
        return {
            'rc': rc,
            'stdout': output[0],
            'stderr': output[1]
        }

    def testConfigCommands(self):
        self.assertFalse(os.path.exists(local_cfg))

        info = self._runConfigScript(['--help'])
        self.assertEqual(info['rc'], 0)
        self.assertEqual(info['stderr'], '')
        self.assertIn('Get and set configuration values for the worker',
                      info['stdout'])

        info = self._runConfigScript(['list'])
        self.assertEqual(info['rc'], 0)
        self.assertIn('[girder_worker]', info['stdout'])

        info = self._runConfigScript(['get', 'celery', 'app_main'])
        self.assertEqual(info['rc'], 0)
        self.assertEqual(info['stdout'].strip(), 'girder_worker')

        info = self._runConfigScript(['set', 'celery', 'app_main', 'foo'])
        self.assertEqual(info['rc'], 0)

        info = self._runConfigScript(['get', 'celery', 'app_main'])
        self.assertEqual(info['rc'], 0)
        self.assertEqual(info['stdout'].strip(), 'foo')

        info = self._runConfigScript(['rm', 'celery', 'app_main'])
        self.assertEqual(info['rc'], 0)

        with self.assertRaises(NoOptionError):
            self._runConfigScript(['get', 'celery', 'app_main'])
