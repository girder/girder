import io
import os
import tempfile

from girder.api import access
from girder.api.describe import Description, describeRoute, autoDescribeRoute
from girder.api.rest import (
    Resource,
    filtermodel,
    iterBody,
    getCurrentUser,
    getApiUrl
)
from girder.models.upload import Upload
from girder.models.item import Item
from girder.models.token import Token
from girder.constants import AccessType

from girder_worker.docker.tasks import docker_run
from girder_worker.docker.transforms import (
    HostStdOut,
    NamedOutputPipe,
    NamedInputPipe,
    Connect,
    VolumePath,
    BindMountVolume,
    ChunkedTransferEncodingStream,
    TemporaryVolume
)
from girder_worker.docker.transforms.girder import (
    GirderFileIdToStream,
    GirderUploadVolumePathToItem,
    ProgressPipe,
    GirderFileIdToVolume,
    GirderItemIdToVolume
)
from girder_worker.utils import JobStatus
from .utilities import wait_for_status

TEST_IMAGE = 'girder/girder_worker_test:ng'


class DockerTestEndpoints(Resource):
    def __init__(self):
        super().__init__()
        self.route('POST', ('test_docker_run', ),
                   self.test_docker_run)
        self.route('POST', ('test_docker_run_mount_volume', ),
                   self.test_docker_run_mount_volume)
        self.route('POST', ('test_docker_run_named_pipe_output', ),
                   self.test_docker_run_named_pipe_output)
        self.route('POST', ('test_docker_run_girder_file_to_named_pipe', ),
                   self.test_docker_run_girder_file_to_named_pipe)
        self.route('POST', ('test_docker_run_file_upload_to_item', ),
                   self.test_docker_run_file_upload_to_item)
        self.route('POST', ('test_docker_run_girder_file_to_named_pipe_on_temp_vol', ),
                   self.test_docker_run_girder_file_to_named_pipe_on_temp_vol)
        self.route('POST', ('test_docker_run_mount_idiomatic_volume', ),
                   self.test_docker_run_mount_idiomatic_volume)
        self.route('POST', ('test_docker_run_progress_pipe', ),
                   self.test_docker_run_progress_pipe)
        self.route('POST', ('test_docker_run_girder_file_to_volume', ),
                   self.test_docker_run_girder_file_to_volume)
        self.route('POST', ('input_stream',), self.input_stream)
        self.route('POST', ('test_docker_run_transfer_encoding_stream', ),
                   self.test_docker_run_transfer_encoding_stream)
        self.route('POST', ('test_docker_run_temporary_volume_root', ),
                   self.test_docker_run_temporary_volume_root)
        self.route('POST', ('test_docker_run_raises_exception', ),
                   self.test_docker_run_raises_exception)
        self.route('POST', ('test_docker_run_cancel', ),
                   self.test_docker_run_cancel)
        self.route('POST', ('test_docker_run_multi_file_item', ),
                   self.test_docker_run_multi_file_item)

    @access.token
    @filtermodel(model='job', plugin='jobs')
    @describeRoute(
        Description('Test basic docker_run.'))
    def test_docker_run(self, params):
        result = docker_run.delay(
            TEST_IMAGE, pull_image=True, container_args=['stdio', '-m', 'hello docker!'],
            remove_container=True)

        return result.job

    @access.token
    @filtermodel(model='job', plugin='jobs')
    @autoDescribeRoute(
        Description('Test GirderItemIdToVolume with multi-file item')
        .modelParam('itemId', 'The item id', model=Item, destName='item',
                    level=AccessType.READ, paramType='query'))
    def test_docker_run_multi_file_item(self, item):
        transform = GirderItemIdToVolume(item['_id'])
        return docker_run.delay(
            TEST_IMAGE, pull_image=True, container_args=['listdir', '-d', transform]
        ).job

    @access.token
    @filtermodel(model='job', plugin='jobs')
    @describeRoute(
        Description('Test docker run that raises an exception.'))
    def test_docker_run_raises_exception(self, params):
        result = docker_run.delay(
            TEST_IMAGE, pull_image=True, container_args=['raise-exception'], remove_container=True)
        return result.job

    @access.token
    @filtermodel(model='job', plugin='jobs')
    @describeRoute(
        Description('Test mounting a volume.'))
    def test_docker_run_mount_volume(self, params):
        fixture_dir = params.get('fixtureDir')
        filename = 'read.txt'
        mount_dir = '/mnt/test'
        mount_path = os.path.join(mount_dir, filename)
        volumes = {
            fixture_dir: {
                'bind': mount_dir,
                'mode': 'ro'
            }
        }
        result = docker_run.delay(
            TEST_IMAGE, pull_image=True, container_args=['read', '-p', mount_path],
            remove_container=True, volumes=volumes)

        return result.job

    @access.token
    @filtermodel(model='job', plugin='jobs')
    @describeRoute(
        Description('Test named pipe output.'))
    def test_docker_run_named_pipe_output(self, params):
        tmp_dir = params.get('tmpDir')
        message = params.get('message')
        mount_dir = '/mnt/girder_worker/data'
        pipe_name = 'output_pipe'

        volumes = {
            tmp_dir: {
                'bind': mount_dir,
                'mode': 'rw'
            }
        }

        connect = Connect(NamedOutputPipe(pipe_name, mount_dir, tmp_dir), HostStdOut())

        result = docker_run.delay(
            TEST_IMAGE, pull_image=True,
            container_args=['write', '-p', connect, '-m', message],
            remove_container=True, volumes=volumes)

        return result.job

    @access.token
    @filtermodel(model='job', plugin='jobs')
    @describeRoute(
        Description('Test downloading file using named pipe.'))
    def test_docker_run_girder_file_to_named_pipe(self, params):
        tmp_dir = params.get('tmpDir')
        file_id = params.get('fileId')
        mount_dir = '/mnt/girder_worker/data'
        pipe_name = 'input_pipe'

        volumes = {
            tmp_dir: {
                'bind': mount_dir,
                'mode': 'rw'
            }
        }

        connect = Connect(GirderFileIdToStream(file_id),
                          NamedInputPipe(pipe_name, mount_dir, tmp_dir))

        result = docker_run.delay(
            TEST_IMAGE, pull_image=True, container_args=['read', '-p', connect],
            remove_container=True, volumes=volumes)

        return result.job

    @access.token
    @filtermodel(model='job', plugin='jobs')
    @describeRoute(
        Description('Test uploading output file to item.'))
    def test_docker_run_file_upload_to_item(self, params):
        item_id = params.get('itemId')
        contents = params.get('contents')

        volumepath = VolumePath('test_file')

        result = docker_run.delay(
            TEST_IMAGE, pull_image=True,
            container_args=['write', '-p', volumepath, '-m', contents],
            remove_container=True,
            girder_result_hooks=[GirderUploadVolumePathToItem(volumepath, item_id)])

        return result.job

    @access.token
    @filtermodel(model='job', plugin='jobs')
    @describeRoute(
        Description('Test downloading file using named pipe.'))
    def test_docker_run_girder_file_to_named_pipe_on_temp_vol(self, params):
        """
        This is a simplified version of test_docker_run_girder_file_to_named_pipe
        it uses the TemporaryVolume, rather than having to setup the volumes
        'manually', this is the approach we should encourage.
        """
        file_id = params.get('fileId')
        pipe_name = 'input_pipe'

        connect = Connect(GirderFileIdToStream(file_id), NamedInputPipe(pipe_name))

        result = docker_run.delay(
            TEST_IMAGE, pull_image=True, container_args=['read', '-p', connect],
            remove_container=True)

        return result.job

    @access.token
    @filtermodel(model='job', plugin='jobs')
    @describeRoute(
        Description('Test idiomatic volume.'))
    def test_docker_run_mount_idiomatic_volume(self, params):
        fixture_dir = params.get('fixtureDir')
        filename = 'read.txt'
        mount_dir = '/mnt/test'
        mount_path = os.path.join(mount_dir, filename)
        volume = BindMountVolume(fixture_dir, mount_path, 'ro')
        volumepath = VolumePath(filename, volume)

        result = docker_run.delay(
            TEST_IMAGE, pull_image=True, container_args=['read', '-p', volumepath],
            remove_container=True, volumes=[volume])

        return result.job

    @access.token
    @filtermodel(model='job', plugin='jobs')
    @describeRoute(
        Description('Test progress pipe.'))
    def test_docker_run_progress_pipe(self, params):
        progressions = params.get('progressions')
        progress_pipe = ProgressPipe()

        result = docker_run.delay(
            TEST_IMAGE, pull_image=True,
            container_args=['progress', '-p', progress_pipe, '--progressions', progressions],
            remove_container=True)

        return result.job

    @access.token
    @filtermodel(model='job', plugin='jobs')
    @describeRoute(
        Description('Test download to volume.'))
    def test_docker_run_girder_file_to_volume(self, params):
        file_id = params.get('fileId')

        result = docker_run.delay(
            TEST_IMAGE, pull_image=True,
            container_args=['read-write', '-i', GirderFileIdToVolume(file_id),
                            '-o', Connect(NamedOutputPipe('out'), HostStdOut())],
            remove_container=True)

        return result.job

    @access.token
    @autoDescribeRoute(
        Description('Accept transfer encoding request. Used by '
                    'test_docker_run_transfer_encoding_stream test case.')
        .modelParam('itemId', 'The item id',
                    model=Item, destName='item',
                    level=AccessType.READ, paramType='query')
        .param('delimiter', 'Delimiter to use when writing out chunks.'))
    def input_stream(self, item, delimiter):
        chunks = io.BytesIO()
        for chunk in iterBody(1):
            chunks.write(chunk)
            chunks.write(delimiter.encode('utf-8'))

        chunks.seek(0)
        contents = chunks.read()
        chunks.seek(0)
        Upload().uploadFromFile(
            chunks, len(contents), 'chunks', parentType='item', parent=item,
            user=getCurrentUser())

    @access.token
    @filtermodel(model='job', plugin='jobs')
    @describeRoute(
        Description('Test transfer encoding stream.'))
    def test_docker_run_transfer_encoding_stream(self, params):
        item_id = params.get('itemId')
        file_id = params.get('fileId')
        delimiter = params.get('delimiter')

        headers = {
            'Girder-Token': str(Token().createToken(getCurrentUser())['_id'])
        }
        url = '%s/%s?itemId=%s&delimiter=%s' % (
            getApiUrl(), 'integration_tests/docker/input_stream', item_id, delimiter)

        container_args = [
            'read-write',
            '-i', GirderFileIdToVolume(file_id),
            '-o', Connect(NamedOutputPipe('out'),
                          ChunkedTransferEncodingStream(url, headers))
        ]
        result = docker_run.delay(
            TEST_IMAGE, pull_image=True, container_args=container_args,
            remove_container=True)

        return result.job

    @access.token
    @filtermodel(model='job', plugin='jobs')
    @describeRoute(
        Description('Test setting temporary volume root.'))
    def test_docker_run_temporary_volume_root(self, params):
        prefix = params.get('prefix')
        root = os.path.join(tempfile.gettempdir(), prefix)
        # We set the mode to 0o777 because the worker container is
        # running as the 'worker' user and needs to be able to have
        # read/write access to the TemporaryVolume
        volume = TemporaryVolume(host_dir=root, mode=0o777)

        result = docker_run.delay(
            TEST_IMAGE, pull_image=True, container_args=['print-path', '-p', volume],
            remove_container=True, volumes=[volume])

        return result.job

    @access.token
    @filtermodel(model='job', plugin='jobs')
    @describeRoute(
        Description('Test cancel docker_run.'))
    def test_docker_run_cancel(self, params):
        mode = params.get('mode')
        result = docker_run.delay(
            TEST_IMAGE, pull_image=True, container_args=[mode],
            remove_container=True)

        assert wait_for_status(self.getCurrentUser(), result.job, JobStatus.RUNNING)
        result.revoke()

        return result.job
