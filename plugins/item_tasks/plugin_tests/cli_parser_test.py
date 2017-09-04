import os

from tests import base

CLI_FILE = os.path.join(
    os.path.abspath(os.path.dirname(__file__)),
    'slicer_cli.xml'
)


def setUpModule():
    base.enabledPlugins.append('item_tasks')
    base.startServer()


def tearDownModule():
    base.stopServer()


class CliParserTest(base.TestCase):

    def test_default_channel(self):
        """Check that parameters with no channel default as inputs."""
        from girder.plugins.item_tasks import cli_parser
        with open(CLI_FILE) as fd:
            spec = cli_parser.parseSlicerCliXml(fd)
            inputs = spec['inputs']

            for input in inputs:
                if input['name'] == 'MinimumSphereActivity':
                    break
            else:
                raise Exception('MinimumSphereActivity not added as an input')
