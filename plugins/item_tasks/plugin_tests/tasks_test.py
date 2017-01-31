import json
import mock
import os
from tests import base


def setUpModule():
    base.enabledPlugins.append('item_tasks')
    base.startServer()


def tearDownModule():
    base.stopServer()


class TasksTest(base.TestCase):
    def setUp(self):
        base.TestCase.setUp(self)

        self.user = self.model('user').createUser(
            login='admin', firstName='admin', lastName='admin', email='a@a.com', password='123456')
        folders = self.model('folder').childFolders(self.user, parentType='user', user=self.user)
        self.privateFolder, self.publicFolder = list(folders)

    def testSlicerCli(self):
        # Create a new item that will become a task
        item = self.model('item').createItem(
            name='placeholder', creator=self.user, folder=self.privateFolder)

        # Create task to introspect container
        with mock.patch('girder.plugins.jobs.models.job.Job.scheduleJob') as scheduleMock:
            resp = self.request(
                '/item_task/%s/slicer_cli_description' % item['_id'], method='POST', params={
                    'image': 'johndoe/foo:v5',
                    'args': json.dumps(['--foo', 'bar'])
                }, user=self.user)
            self.assertStatusOk(resp)
            self.assertEqual(resp.json['_modelType'], 'job')
            self.assertEqual(len(scheduleMock.mock_calls), 1)
            job = scheduleMock.mock_calls[0][1][0]
            self.assertEqual(job['handler'], 'worker_handler')
            self.assertEqual(job['itemTaskId'], item['_id'])

        # Task should not be registered until we get the callback
        resp = self.request('/item_task', user=self.user)
        self.assertStatusOk(resp)
        self.assertEqual(resp.json, [])

        # Image and args should be stored in the item metadata
        item = self.model('item').load(item['_id'], force=True)
        self.assertEqual(item['meta']['itemTaskSpec']['docker_image'], 'johndoe/foo:v5')
        self.assertEqual(item['meta']['itemTaskSlicerCliArgs'], ['--foo', 'bar'])

        # Simulate callback from introspection job
        with open(os.path.join(os.path.dirname(__file__), 'slicer_cli.xml')) as f:
            xml = f.read()

        resp = self.request(
            '/item_task/%s/slicer_cli_xml' % item['_id'], method='PUT', params={
                'setName': True,
                'setDescription': True
            }, user=self.user, body=xml, type='application/xml')
        self.assertStatusOk(resp)

        # We should only be able to see tasks we have read access on
        resp = self.request('/item_task')
        self.assertStatusOk(resp)
        self.assertEqual(resp.json, [])

        resp = self.request('/item_task', user=self.user)
        self.assertStatusOk(resp)
        self.assertEqual(len(resp.json), 1)
        self.assertEqual(resp.json[0]['_id'], str(item['_id']))
        item = self.model('item').load(item['_id'], force=True)
        self.assertEqual(item['meta']['itemTaskSpec'], {
            'mode': 'docker',
            'docker_image': 'johndoe/foo:v5',
            'container_args': [
                '--foo', 'bar', '--InputImage', '$input{--InputImage}',
                '--MaximumLineStraightnessDeviation',
                '$input{--MaximumLineStraightnessDeviation}', '--MaximumRadius',
                '$input{--MaximumRadius}', '--MaximumSphereDistance',
                '$input{--MaximumSphereDistance}', '--MinimumRadius',
                '$input{--MinimumRadius}', '--MinimumSphereActivity',
                '$input{--MinimumSphereActivity}', '--MinimumSphereDistance',
                '$input{--MinimumSphereDistance}', '--SpheresPerPhantom',
                '$input{--SpheresPerPhantom}', '$flag{--StrictSorting}',
                '--DetectedPoints', '/mnt/girder_worker/data/--DetectedPoints'
            ],
            'inputs': [{
                'description': 'Input image to be analysed.',
                'format': 'file',
                'name': 'InputImage', 'type': 'file', 'id': '--InputImage',
                'target': 'filepath'
            }, {
                'description': 'Used for eliminating detections which are not in a straight line. '
                               'Unit: multiples of geometric average of voxel spacing',
                'format': 'number',
                'default': {'data': 1.0},
                'type': 'number',
                'id': '--MaximumLineStraightnessDeviation',
                'name': 'MaximumLineStraightnessDeviation'
            }, {
                'description': 'Used for eliminating too big blobs. Unit: millimeter [mm]',
                'format': 'number', 'default': {'data': 20.0},
                'type': 'number',
                'id': '--MaximumRadius',
                'name': 'MaximumRadius'
            }, {
                'description': 'Signifies maximum distance between adjacent sphere centers [mm]. '
                               'Used to separate phantoms from tumors.',
                'format': 'number', 'default': {'data': 40.0},
                'type': 'number',
                'id': '--MaximumSphereDistance',
                'name': 'MaximumSphereDistance'
            }, {
                'description': 'Used for eliminating too small blobs. Unit: millimeter [mm]',
                'format': 'number',
                'default': {'data': 3.0},
                'type': 'number',
                'id': '--MinimumRadius',
                'name': 'MinimumRadius'
            }, {
                'description': 'Used for thresholding in blob detection. '
                               'Unit: becquerels per milliliter [Bq/ml]',
                'format': 'number', 'default': {'data': 5000.0},
                'type': 'number',
                'id': '--MinimumSphereActivity',
                'name': 'MinimumSphereActivity'
            }, {
                'description': 'Signifies minimum distance between adjacent sphere centers [mm]. '
                               'Used to separate phantoms from tumors.',
                'format': 'number',
                'default': {'data': 30.0},
                'type': 'number',
                'id': '--MinimumSphereDistance',
                'name': 'MinimumSphereDistance'
            }, {
                'description': 'What kind of phantom are we working with here?',
                'format': 'integer',
                'default': {'data': 3},
                'type': 'integer',
                'id': '--SpheresPerPhantom',
                'name': 'SpheresPerPhantom'
            }, {
                'description': 'Controls whether spheres within a phantom must have descending '
                               'activities. If OFF, they can have approximately same activities '
                               '(within 15%).',
                'format': 'boolean',
                'default': {'data': False},
                'type': 'boolean',
                'id': '--StrictSorting',
                'name': 'StrictSorting'
            }],
            'outputs': [{
                'description': 'Fiducual points, one for each detected sphere. '
                               'Will be multiple of 3.',
                'format': 'new-file',
                'name': 'DetectedPoints',
                'type': 'new-file',
                'id': '--DetectedPoints',
                'target': 'filepath'
            }]
        })
