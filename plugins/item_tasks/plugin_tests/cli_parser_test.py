import os

from tests import base
from girder_plugin_item_tasks import cli_parser

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

    def parse_file(self, fileName):
        """Open an parse the given slicer cli spec."""
        fullPath = os.path.join(
            os.path.abspath(os.path.dirname(__file__)),
            fileName
        )
        with open(fullPath) as fd:
            spec = cli_parser.parseSlicerCliXml(fd)
        return spec

    def test_default_channel(self):
        """Check that parameters with no channel default as inputs."""
        spec = self.parse_file('slicer_cli.xml')
        inputs = spec['inputs']

        for input in inputs:
            if input['name'] == 'MinimumSphereActivity':
                break
        else:
            raise Exception('MinimumSphereActivity not added as an input')

    def test_vector_type_conversion(self):
        """Check that slicer vector types are correctly converted."""
        spec = self.parse_file('nuclei_detection.xml')
        inputs = spec['inputs']
        for input in inputs:
            if input['name'] == 'Reference Mean LAB':
                self.assertEqual(input['type'], 'number-vector')
                break
        else:
            raise Exception('reference_mu_lab not added as an input')

    def test_region_type_conversion(self):
        """Check that the region type is parsed correctly."""
        spec = self.parse_file('nuclei_detection.xml')
        inputs = spec['inputs']
        for input in inputs:
            if input['name'] == 'Analysis ROI':
                self.assertEqual(input['type'], 'region')
                break
        else:
            raise Exception('analysis_roi not added as an input')

    def test_image_parameter(self):
        """Check that parameters of type image are handled correctly."""
        spec = self.parse_file('slicer_cli.xml')

        inputs = spec['inputs']
        for input in inputs:
            if input['name'] == 'InputImage':
                self.assertEqual(input['type'], 'image')
                break
        else:
            raise Exception('InputImage not added to spec.')
