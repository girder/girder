import json
import mock
import os
import time

from girder.constants import AccessType
from tests import base


def setUpModule():
    base.enabledPlugins.append('item_tasks')
    base.startServer()


def tearDownModule():
    base.stopServer()


class TasksTest(base.TestCase):
    def setUp(self):
        base.TestCase.setUp(self)

        self.admin = self.model('user').createUser(
            login='admin', firstName='admin', lastName='admin', email='a@a.com', password='123456')
        self.user = self.model('user').createUser(
            login='user1', firstName='user', lastName='1', email='u@u.com', password='123456')
        folders = self.model('folder').childFolders(self.admin, parentType='user', user=self.admin)
        self.privateFolder, self.publicFolder = list(folders)

    def testAddItemTasksToFolderFromJson(self):
        """
        Test adding item tasks to a folder from a JSON spec.
        """
        # Create a new folder that will contain the tasks
        folder = self.model('folder').createFolder(
            name='placeholder', creator=self.admin, parent=self.admin, parentType='user')

        # Create task to introspect container
        with mock.patch('girder.plugins.jobs.models.job.Job.scheduleJob') as scheduleMock:
            resp = self.request(
                '/folder/%s/item_task_json_description' % folder['_id'], method='POST', params={
                    'image': 'johndoe/foo:v5'
                }, user=self.admin)
            self.assertStatusOk(resp)
            self.assertEqual(resp.json['_modelType'], 'job')
            self.assertEqual(len(scheduleMock.mock_calls), 1)
            job = scheduleMock.mock_calls[0][1][0]
            self.assertEqual(job['handler'], 'worker_handler')
            self.assertEqual(job['itemTaskId'], folder['_id'])
            self.assertEqual(job['kwargs']['outputs']['_stdout']['method'], 'POST')
            self.assertTrue(job['kwargs']['outputs']['_stdout']['url'].endswith(
                'folder/%s/item_task_json_specs' % folder['_id']))
            params = job['kwargs']['outputs']['_stdout']['params']
            self.assertEqual(params['image'], 'johndoe/foo:v5')
            self.assertEqual(params['pullImage'], True)
            token = job['kwargs']['outputs']['_stdout']['headers']['Girder-Token']

        # Task should not be registered until we get the callback
        resp = self.request('/item_task', user=self.admin)
        self.assertStatusOk(resp)
        self.assertEqual(resp.json, [])

        # Simulate callback from introspection job
        with open(os.path.join(os.path.dirname(__file__), 'specs.json')) as f:
            specs = f.read()

        parsedSpecs = json.loads(specs)

        resp = self.request(
            '/folder/%s/item_task_json_specs' % folder['_id'], method='POST', params={
                'image': 'johndoe/foo:v5',
                'pullImage': False
            }, token=token, body=specs, type='application/json')

        self.assertStatusOk(resp)

        items = list(self.model('folder').childItems(folder, user=self.admin))
        self.assertEqual(len(items), 2)

        # Image name and item task flag should be stored in the item metadata
        for itemIndex, item in enumerate(items):
            item = self.model('item').load(item['_id'], force=True)
            self.assertEqual(item['name'], 'johndoe/foo:v5 %s' % (str(itemIndex)))
            self.assertEqual(item['description'], parsedSpecs[itemIndex]['description'])
            self.assertTrue(item['meta']['isItemTask'])
            parsedSpecs[itemIndex]['pull_image'] = False
            parsedSpecs[itemIndex]['docker_image'] = 'johndoe/foo:v5'
            self.assertEqual(item['meta']['itemTaskSpec'], parsedSpecs[itemIndex])
            self.assertEqual(item['meta']['itemTaskName'], '')

        # We should only be able to see tasks we have read access on
        resp = self.request('/item_task')
        self.assertStatusOk(resp)
        self.assertEqual(resp.json, [])

        resp = self.request('/item_task', user=self.admin)
        self.assertStatusOk(resp)
        self.assertEqual(len(resp.json), 2)

        # Test adding single task spec
        folder2 = self.model('folder').createFolder(
            name='placeholder2', creator=self.admin, parent=self.admin, parentType='user')
        with open(os.path.join(os.path.dirname(__file__), 'spec.json')) as f:
            spec = f.read()
        parsedSpec = json.loads(spec)

        token = self.model('token').createToken(
            user=self.admin, scope='item_task.set_task_spec.%s' % folder2['_id'])
        resp = self.request(
            '/folder/%s/item_task_json_specs' % folder2['_id'], method='POST', params={
                'image': 'johndoe/foo:v5',
                'pullImage': False
            },
            token=token, body=spec, type='application/json')
        self.assertStatusOk(resp)
        items = list(self.model('folder').childItems(folder2, user=self.admin))
        self.assertEqual(len(items), 1)

        # Check that the single item has the correct metadata
        item = self.model('item').load(items[0]['_id'], force=True)
        self.assertEqual(item['name'], 'johndoe/foo:v5')
        self.assertEqual(item['description'], parsedSpec['description'])
        self.assertTrue(item['meta']['isItemTask'])
        parsedSpec['pull_image'] = False
        parsedSpec['docker_image'] = 'johndoe/foo:v5'
        self.assertEqual(item['meta']['itemTaskSpec'], parsedSpec)
        self.assertEqual(item['meta']['itemTaskName'], '')

    def testItemTaskGetEndpointMinMax(self):
        """
        Test adding item tasks to a folder from a JSON spec.
        """
        with open(os.path.join(os.path.dirname(__file__), 'namedSpecs.json')) as f:
            specs = f.read()

        def createTask(itemName, taskName, specs=specs):
            # Create a new item that will become a task
            item = self.model('item').createItem(
                name=itemName, creator=self.admin, folder=self.privateFolder)
            # Create task to introspect container
            with mock.patch('girder.plugins.jobs.models.job.Job.scheduleJob') as scheduleMock:
                resp = self.request(
                    '/item/%s/item_task_json_description' % item['_id'], method='POST', params={
                        'image': 'johndoe/foo:v5',
                        'taskName': taskName
                    }, user=self.admin)
                self.assertStatusOk(resp)
                job = scheduleMock.mock_calls[0][1][0]
                token = job['kwargs']['outputs']['_stdout']['headers']['Girder-Token']

            # Simulate callback with a valid task name
            resp = self.request(
                '/item/%s/item_task_json_specs' % (item['_id']), method='PUT', params={
                    'image': 'johndoe/foo:v5',
                    'taskName': taskName,
                    'setName': True,
                    'setDescription': True,
                    'pullImage': False
                },
                token=token, body=specs, type='application/json')
            self.assertStatusOk(resp)

        # Test GET endpoint
        def testMinMax(expected, min=0, max=None):
            if max is None:
                params = {
                    'minFileInputs': min
                    }
            else:
                params = {
                    'minFileInputs': min,
                    'maxFileInputs': max
                }
            resp = self.request(
                '/item_task', params=params,
                user=self.admin)
            self.assertStatusOk(resp)
            self.assertEqual(len(resp.json), expected)

        createTask('item1', 'Task 1')
        createTask('item2', '1 File Task')
        createTask('item3', '2 File Task')
        createTask('item4', '3 File Task')
        testMinMax(1, min=1, max=1)
        testMinMax(4, max=3)
        testMinMax(3, max=2)
        testMinMax(2, min=2, max=3)
        testMinMax(4)
        testMinMax(1, min=3)

    def testConfigureItemTaskFromJson(self):
        """
        Test configuring an item with a task from a JSON spec, then reconfiguring the
        item with a different task from the JSON spec.
        """
        # Create a new item that will become a task
        item = self.model('item').createItem(
            name='placeholder', creator=self.admin, folder=self.privateFolder)

        # Create job to introspect container
        with mock.patch('girder.plugins.jobs.models.job.Job.scheduleJob') as scheduleMock:
            resp = self.request(
                '/item/%s/item_task_json_description' % item['_id'], method='POST', params={
                    'image': 'johndoe/foo:v5',
                    'taskName': 'Task 2'
                }, user=self.admin)
            self.assertStatusOk(resp)
            self.assertEqual(resp.json['_modelType'], 'job')
            self.assertEqual(len(scheduleMock.mock_calls), 1)
            job = scheduleMock.mock_calls[0][1][0]
            self.assertEqual(job['handler'], 'worker_handler')
            self.assertEqual(job['itemTaskId'], item['_id'])
            self.assertEqual(job['kwargs']['outputs']['_stdout']['method'], 'PUT')
            self.assertTrue(job['kwargs']['outputs']['_stdout']['url'].endswith(
                'item/%s/item_task_json_specs' % item['_id']))
            params = job['kwargs']['outputs']['_stdout']['params']
            self.assertEqual(params['image'], 'johndoe/foo:v5')
            self.assertEqual(params['taskName'], 'Task 2')
            self.assertEqual(params['setName'], True)
            self.assertEqual(params['setDescription'], True)
            self.assertEqual(params['pullImage'], True)
            token = job['kwargs']['outputs']['_stdout']['headers']['Girder-Token']

        # Task should not be registered until we get the callback
        resp = self.request('/item_task', user=self.admin)
        self.assertStatusOk(resp)
        self.assertEqual(resp.json, [])

        # Simulate callback from introspection job
        with open(os.path.join(os.path.dirname(__file__), 'namedSpecs.json')) as f:
            specs = f.read()

        # Simulate callback with an invalid task name
        resp = self.request(
            '/item/%s/item_task_json_specs' % (item['_id']), method='PUT', params={
                'image': 'johndoe/foo:v5',
                'taskName': 'Invalid task'
            },
            token=token, body=specs, type='application/json')
        self.assertStatus(resp, 400)

        # Simulate callback with a valid task name
        resp = self.request(
            '/item/%s/item_task_json_specs' % (item['_id']), method='PUT', params={
                'image': 'johndoe/foo:v5',
                'taskName': 'Task 2',
                'setName': True,
                'setDescription': True,
                'pullImage': False
            },
            token=token, body=specs, type='application/json')
        self.assertStatusOk(resp)

        # We should only be able to see tasks we have read access on
        resp = self.request('/item_task')
        self.assertStatusOk(resp)
        self.assertEqual(resp.json, [])

        resp = self.request('/item_task', user=self.admin)
        self.assertStatusOk(resp)
        self.assertEqual(len(resp.json), 1)
        self.assertEqual(resp.json[0]['_id'], str(item['_id']))

        # Check that the item has the correct metadata
        item = self.model('item').load(item['_id'], force=True)
        self.assertEqual(item['name'], 'Task 2')
        self.assertEqual(item['description'], 'Task 2 description')
        self.assertTrue(item['meta']['isItemTask'])
        self.assertEqual(item['meta']['itemTaskName'], 'Task 2')
        self.assertEqual(item['meta']['itemTaskSpec']['name'], 'Task 2')
        self.assertEqual(item['meta']['itemTaskSpec']['description'], 'Task 2 description')
        self.assertEqual(item['meta']['itemTaskSpec']['mode'], 'docker')
        self.assertEqual(item['meta']['itemTaskSpec']['inputs'], [])
        self.assertEqual(item['meta']['itemTaskSpec']['outputs'], [])

        # Create job to introspect container
        with mock.patch('girder.plugins.jobs.models.job.Job.scheduleJob') as scheduleMock:
            resp = self.request(
                '/item/%s/item_task_json_description' % item['_id'], method='POST', params={
                    'image': 'johndoe/foo:v5',
                    'taskName': 'Task 1'
                }, user=self.admin)
            self.assertStatusOk(resp)
            self.assertEqual(resp.json['_modelType'], 'job')
            self.assertEqual(len(scheduleMock.mock_calls), 1)
            job = scheduleMock.mock_calls[0][1][0]
            self.assertEqual(job['handler'], 'worker_handler')
            self.assertEqual(job['itemTaskId'], item['_id'])
            self.assertEqual(job['kwargs']['outputs']['_stdout']['method'], 'PUT')
            self.assertTrue(job['kwargs']['outputs']['_stdout']['url'].endswith(
                'item/%s/item_task_json_specs' % item['_id']))
            params = job['kwargs']['outputs']['_stdout']['params']
            self.assertEqual(params['image'], 'johndoe/foo:v5')
            self.assertEqual(params['taskName'], 'Task 1')
            self.assertEqual(params['setName'], True)
            self.assertEqual(params['setDescription'], True)
            self.assertEqual(params['pullImage'], True)
            token = job['kwargs']['outputs']['_stdout']['headers']['Girder-Token']

        # Simulate callback from introspection job
        resp = self.request(
            '/item/%s/item_task_json_specs' % item['_id'], method='PUT', params={
                'image': 'johndoe/foo:v5',
                'taskName': 'Task 1',
                'setName': True,
                'setDescription': True,
                'pullImage': False
            },
            token=token, body=specs, type='application/json')
        self.assertStatusOk(resp)

        resp = self.request('/item_task', user=self.admin)
        self.assertStatusOk(resp)
        self.assertEqual(len(resp.json), 1)
        self.assertEqual(resp.json[0]['_id'], str(item['_id']))

        # Check that the item has the correct metadata
        item = self.model('item').load(item['_id'], force=True)
        self.assertEqual(item['name'], 'Task 1')
        self.assertEqual(item['description'], 'Task 1 description')
        self.assertTrue(item['meta']['isItemTask'])
        self.assertEqual(item['meta']['itemTaskName'], 'Task 1')
        self.assertEqual(item['meta']['itemTaskSpec']['name'], 'Task 1')
        self.assertEqual(item['meta']['itemTaskSpec']['description'], 'Task 1 description')
        self.assertEqual(item['meta']['itemTaskSpec']['mode'], 'docker')
        self.assertEqual(item['meta']['itemTaskSpec']['inputs'], [{
            'id': 'dummy_input',
            'name': 'Dummy input',
            'description': 'Dummy input flag',
            'type': 'boolean',
            'default': {'data': True}
        }])
        self.assertEqual(item['meta']['itemTaskSpec']['outputs'], [])

    def testAddItemTasksToFolderFromSlicerCli(self):
        """
        Test adding item tasks to a folder from Slicer CLI XML.
        """
        # Create a new folder that will contain the tasks
        folder = self.model('folder').createFolder(
            name='placeholder', creator=self.admin, parent=self.admin, parentType='user')

        # Create task to introspect container
        with mock.patch('girder.plugins.jobs.models.job.Job.scheduleJob') as scheduleMock:
            resp = self.request(
                '/folder/%s/item_task_slicer_cli_description' % folder['_id'], method='POST',
                params={
                    'image': 'johndoe/foo:v5',
                    'args': json.dumps(['--foo', 'bar'])
                }, user=self.admin)
            self.assertStatusOk(resp)
            self.assertEqual(resp.json['_modelType'], 'job')
            self.assertEqual(len(scheduleMock.mock_calls), 1)
            job = scheduleMock.mock_calls[0][1][0]
            self.assertEqual(job['handler'], 'worker_handler')
            self.assertEqual(job['itemTaskId'], folder['_id'])
            self.assertEqual(job['kwargs']['outputs']['_stdout']['method'], 'POST')
            self.assertTrue(job['kwargs']['outputs']['_stdout']['url'].endswith(
                'folder/%s/item_task_slicer_cli_xml' % folder['_id']))
            params = job['kwargs']['outputs']['_stdout']['params']
            self.assertEqual(params['image'], 'johndoe/foo:v5')
            self.assertEqual(params['args'], '["--foo", "bar"]')
            self.assertEqual(params['pullImage'], True)
            token = job['kwargs']['outputs']['_stdout']['headers']['Girder-Token']

        # Task should not be registered until we get the callback
        resp = self.request('/item_task', user=self.admin)
        self.assertStatusOk(resp)
        self.assertEqual(resp.json, [])

        # Simulate callback from introspection job
        with open(os.path.join(os.path.dirname(__file__), 'slicer_cli.xml')) as f:
            xml = f.read()

        resp = self.request(
            '/folder/%s/item_task_slicer_cli_xml' % folder['_id'], method='POST', params={
                'image': 'johndoe/foo:v5',
                'args': json.dumps(['--foo', 'bar']),
                'pullImage': False
            },
            token=token, body=xml, type='application/xml')
        self.assertStatusOk(resp)

        # We should only be able to see tasks we have read access on
        resp = self.request('/item_task')
        self.assertStatusOk(resp)
        self.assertEqual(resp.json, [])

        resp = self.request('/item_task', user=self.admin)
        self.assertStatusOk(resp)
        self.assertEqual(len(resp.json), 1)

        items = list(self.model('folder').childItems(folder, user=self.admin))
        self.assertEqual(len(items), 1)
        item = items[0]

        # Image name and item task flag should be stored in the item metadata
        self.assertEqual(item['name'], 'PET phantom detector CLI')
        self.assertEqual(
            item['description'],
            u'**Description**: Detects positions of PET/CT pocket phantoms in PET image.\n\n'
            u'**Author(s)**: D\u017eenan Zuki\u0107\n\n**Version**: 1.0\n\n'
            u'**License**: Apache 2.0\n\n**Acknowledgements**: *none*\n\n'
            u'*This description was auto-generated from the Slicer CLI XML specification.*'
        )
        self.assertTrue(item['meta']['isItemTask'])
        self.assertHasKeys(item['meta']['itemTaskSpec'],
                           ('mode', 'docker_image', 'container_args', 'inputs', 'outputs'))
        self.assertEqual(item['meta']['itemTaskSpec']['mode'], 'docker')
        self.assertEqual(item['meta']['itemTaskSpec']['docker_image'], 'johndoe/foo:v5')
        self.assertEqual(item['meta']['itemTaskSlicerCliArgs'], ['--foo', 'bar'])

    def testConfigureItemTaskFromSlicerCli(self):
        # Create a new item that will become a task
        item = self.model('item').createItem(
            name='placeholder', creator=self.admin, folder=self.privateFolder)

        # Create task to introspect container
        with mock.patch('girder.plugins.jobs.models.job.Job.scheduleJob') as scheduleMock:
            resp = self.request(
                '/item/%s/item_task_slicer_cli_description' % item['_id'], method='POST', params={
                    'image': 'johndoe/foo:v5',
                    'args': json.dumps(['--foo', 'bar'])
                }, user=self.admin)
            self.assertStatusOk(resp)
            self.assertEqual(resp.json['_modelType'], 'job')
            self.assertEqual(len(scheduleMock.mock_calls), 1)
            job = scheduleMock.mock_calls[0][1][0]
            self.assertEqual(job['handler'], 'worker_handler')
            self.assertEqual(job['itemTaskId'], item['_id'])
            self.assertEqual(job['kwargs']['outputs']['_stdout']['method'], 'PUT')
            self.assertTrue(job['kwargs']['outputs']['_stdout']['url'].endswith(
                'item/%s/item_task_slicer_cli_xml' % item['_id']))
            token = job['kwargs']['outputs']['_stdout']['headers']['Girder-Token']

        # Task should not be registered until we get the callback
        resp = self.request('/item_task', user=self.admin)
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
            '/item/%s/item_task_slicer_cli_xml' % item['_id'], method='PUT', params={
                'setName': True,
                'setDescription': True
            }, token=token, body=xml, type='application/xml')
        self.assertStatusOk(resp)

        # We should only be able to see tasks we have read access on
        resp = self.request('/item_task')
        self.assertStatusOk(resp)
        self.assertEqual(resp.json, [])

        resp = self.request('/item_task', user=self.admin)
        self.assertStatusOk(resp)
        self.assertEqual(len(resp.json), 1)
        self.assertEqual(resp.json[0]['_id'], str(item['_id']))

        item = self.model('item').load(item['_id'], force=True)
        self.assertEqual(item['name'], 'PET phantom detector CLI')
        self.assertEqual(
            item['description'],
            u'**Description**: Detects positions of PET/CT pocket phantoms in PET image.\n\n'
            u'**Author(s)**: D\u017eenan Zuki\u0107\n\n**Version**: 1.0\n\n'
            u'**License**: Apache 2.0\n\n**Acknowledgements**: *none*\n\n'
            u'*This description was auto-generated from the Slicer CLI XML specification.*'
        )
        self.assertTrue(item['meta']['isItemTask'])
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
                '--DetectedPoints', '$output{--DetectedPoints}'
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
                'format': 'number-enumeration',
                'default': {'data': 3},
                'type': 'number-enumeration',
                'id': '--SpheresPerPhantom',
                'name': 'SpheresPerPhantom',
                'values': [2, 3]
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

        # Shouldn't be able to run the task if we don't have execute permission flag
        self.model('folder').setUserAccess(
            self.privateFolder, user=self.user, level=AccessType.READ, save=True)
        resp = self.request(
            '/item_task/%s/execution' % item['_id'], method='POST', user=self.user)
        self.assertStatus(resp, 403)

        # Grant the user permission, and run the task
        from girder.plugins.item_tasks.constants import ACCESS_FLAG_EXECUTE_TASK
        self.model('folder').setUserAccess(
            self.privateFolder, user=self.user, level=AccessType.WRITE,
            flags=ACCESS_FLAG_EXECUTE_TASK, currentUser=self.admin, save=True)

        inputs = {
            '--InputImage': {
                'mode': 'girder',
                'resource_type': 'item',
                'id': str(item['_id'])
            },
            '--MaximumLineStraightnessDeviation': {
                'mode': 'inline',
                'data': 1
            },
            '--MaximumRadius': {
                'mode': 'inline',
                'data': 20
            },
            '--MaximumSphereDistance': {
                'mode': 'inline',
                'data': 40
            },
            '--MinimumRadius': {
                'mode': 'inline',
                'data': 3
            },
            '--MinimumSphereActivity': {
                'mode': 'inline',
                'data': 5000
            },
            '--MinimumSphereDistance': {
                'mode': 'inline',
                'data': 30
            },
            '--SpheresPerPhantom': {
                'mode': 'inline',
                'data': 3},
            '--StrictSorting': {
                'mode': 'inline',
                'data': False
            }
        }

        outputs = {
            '--DetectedPoints': {
                'mode': 'girder',
                'parent_id': str(self.privateFolder['_id']),
                'parent_type': 'folder',
                'name': 'test.txt'
            }
        }

        # Ensure task was scheduled
        with mock.patch('girder.plugins.jobs.models.job.Job.scheduleJob') as scheduleMock:
            resp = self.request(
                '/item_task/%s/execution' % item['_id'], method='POST', user=self.user, params={
                    'inputs': json.dumps(inputs),
                    'outputs': json.dumps(outputs)
                })
            self.assertEqual(len(scheduleMock.mock_calls), 1)
        self.assertStatusOk(resp)
        job = resp.json
        self.assertEqual(job['_modelType'], 'job')
        self.assertNotIn('kwargs', job)  # ordinary user can't see kwargs

        jobModel = self.model('job', 'jobs')
        job = jobModel.load(job['_id'], force=True)
        output = job['kwargs']['outputs']['--DetectedPoints']

        # Simulate output from the worker
        contents = b'Hello world'
        resp = self.request(
            path='/file', method='POST', token=output['token'], params={
                'parentType': output['parent_type'],
                'parentId': output['parent_id'],
                'name': output['name'],
                'size': len(contents),
                'mimeType': 'text/plain',
                'reference': output['reference']
            })
        self.assertStatusOk(resp)

        uploadId = resp.json['_id']
        fields = [('offset', 0), ('uploadId', uploadId)]
        files = [('chunk', output['name'], contents)]
        resp = self.multipartRequest(
            path='/file/chunk', fields=fields, files=files, token=output['token'])
        self.assertStatusOk(resp)
        file = resp.json
        self.assertEqual(file['_modelType'], 'file')
        self.assertEqual(file['size'], 11)
        self.assertEqual(file['mimeType'], 'text/plain')
        file = self.model('file').load(file['_id'], force=True)

        # Make sure temp token is removed once we change job status to final state
        job = jobModel.load(job['_id'], force=True)
        self.assertIn('itemTaskTempToken', job)

        from girder.plugins.jobs.constants import JobStatus
        job = jobModel.updateJob(job, status=JobStatus.SUCCESS)

        self.assertNotIn('itemTaskTempToken', job)
        self.assertIn('itemTaskBindings', job)

        # Wait for async data.process event to bind output provenance
        start = time.time()
        while time.time() - start < 15:
            job = jobModel.load(job['_id'], force=True)

            if 'itemId' in job['itemTaskBindings']['outputs']['--DetectedPoints']:
                break
            else:
                time.sleep(0.2)
        else:
            raise Exception('Output binding did not occur in time')

        self.assertEqual(
            job['itemTaskBindings']['outputs']['--DetectedPoints']['itemId'], file['itemId'])
