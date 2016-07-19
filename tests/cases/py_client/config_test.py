import contextlib
import mock
import os
import girder_client
import girder_client.configure
import unittest
import sys
import six
from six.moves.configparser import ConfigParser, NoOptionError


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

LOCAL_CFG = os.path.join(girder_client.CONFIG_DIR, "girder-cli.conf")


def setUpModule():
    # Backup local config file if it exists
    if os.path.exists(LOCAL_CFG):
        os.rename(LOCAL_CFG, LOCAL_CFG + '.bak')
        # Re-read the config
        girder_client.config = ConfigParser(girder_client._config_defaults,
                                            allow_no_value=True)
        if not girder_client.config.has_section("girder_client"):
            girder_client.config.add_section("girder_client")


def tearDownModule():
    # Restore local config from backup if it exists
    if os.path.exists(LOCAL_CFG + '.bak'):
        os.rename(LOCAL_CFG + '.bak', LOCAL_CFG)


class TestConfigScript(unittest.TestCase):
    def _runConfigScript(self, args):
        args = ['girder-cli-config'] + args
        rc = 0
        with mock.patch.object(sys, 'argv', args),\
                mock.patch('sys.exit', side_effect=SysExitException) as exit,\
                captureOutput() as output:
            try:
                girder_client.configure.main()
            except SysExitException:
                args = exit.mock_calls[0][1]
                rc = args[0] if len(args) else 0
        return {
            'rc': rc,
            'stdout': output[0],
            'stderr': output[1]
        }

    def testConfigCommands(self):
        self.assertFalse(os.path.exists(LOCAL_CFG))

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
        self.assertEqual(info['stdout'].strip(), 'localhost')

        info = self._runConfigScript(['set', 'girder_client', 'port', '80'])
        self.assertEqual(info['rc'], 0)

        info = self._runConfigScript(['get', 'girder_client', 'port'])
        self.assertEqual(info['rc'], 0)
        self.assertEqual(info['stdout'].strip(), '80')

        info = self._runConfigScript(['rm', 'girder_client', 'port'])
        self.assertEqual(info['rc'], 0)

        with self.assertRaises(NoOptionError):
            self._runConfigScript(['get', 'girder_client', 'foo'])
