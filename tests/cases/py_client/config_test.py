import contextlib
import mock
import os
import tempfile
import girder_client.configure as gcfg
import unittest
import sys
import six
from six.moves.configparser import NoOptionError


@contextlib.contextmanager
def captureOutput():
    oldout, olderr = sys.stdout, sys.stderr
    try:
        out = [six.StringIO(), six.StringIO()]
        sys.stdout, sys.stderr = out
        yield out
    finally:
        sys.stdout, sys.stderr = oldout, olderr
        out[0] = out[0].getvalue()
        out[1] = out[1].getvalue()


class SysExitException(Exception):
    pass


def setUpModule():
    # Backup local config file if it exists
    config = gcfg.GirderConfig()
    if os.path.exists(config.config_file):
        os.rename(config.config_file, config.config_file + '.bak')


def tearDownModule():
    # Restore local config from backup if it exists
    config = gcfg.GirderConfig()
    if os.path.exists(config.config_file + '.bak'):
        os.rename(config.config_file + '.bak', config.config_file)


class TestConfigScript(unittest.TestCase):

    def _runConfigScript(self, args):
        args = ['girder-cli-config'] + args
        rc = 0
        with mock.patch.object(sys, 'argv', args),\
                mock.patch('sys.exit', side_effect=SysExitException) as exit,\
                captureOutput() as output:
            try:
                gcfg.main()
            except SysExitException:
                args = exit.mock_calls[0][1]
                rc = args[0] if len(args) else 0
        return {
            'rc': rc,
            'stdout': output[0],
            'stderr': output[1]
        }

    def testConfigCommands(self):
        self.assertFalse(os.path.exists(gcfg.GirderConfig().config_file))

        info = self._runConfigScript(['--help'])
        self.assertEqual(info['rc'], 0)
        self.assertEqual(info['stderr'], '')
        self.assertIn('Get and set configuration values for the client',
                      info['stdout'])

        info = self._runConfigScript(['list'])
        self.assertEqual(info['rc'], 0)
        self.assertIn('[girder_client]', info['stdout'])

        info = self._runConfigScript(['get', 'girder_client', 'host'])
        self.assertEqual(info['rc'], 0)
        self.assertEqual(info['stdout'].split()[-1].strip(), 'localhost')

        info = self._runConfigScript(['set', 'girder_client', 'port', '82'])
        self.assertEqual(info['rc'], 0)

        info = self._runConfigScript(['get', 'girder_client', 'port'])
        self.assertEqual(info['rc'], 0)
        self.assertEqual(info['stdout'].strip(), '82')

        info = self._runConfigScript(['rm', 'girder_client', 'port'])
        self.assertEqual(info['rc'], 0)

        with self.assertRaises(NoOptionError):
            self._runConfigScript(['get', 'girder_client', 'foo'])

        tmpcfg_fd, tmpcfg_fname = tempfile.mkstemp()
        with open(tmpcfg_fname, 'w') as fh:
            gcfg.GirderConfig().writeConfig(fh)

        info = self._runConfigScript(['-c', tmpcfg_fname, 'set',
                                      'girder_client', 'port', '90'])
        self.assertEqual(info['rc'], 0)
        info = self._runConfigScript(['-c', tmpcfg_fname, 'get',
                                      'girder_client', 'port'])
        self.assertEqual(info['rc'], 0)
        self.assertEqual(info['stdout'].strip(), '90')

        info = self._runConfigScript(['get', 'girder_client', 'port'])
        self.assertEqual(info['rc'], 0)
        self.assertEqual(info['stdout'].strip(), 'None')

        os.close(tmpcfg_fd)
        os.remove(tmpcfg_fname)
