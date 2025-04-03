import datetime
import json
import os
import shutil
import socket
import sys
import threading
import time
try:
    import docker
    from docker.errors import DockerException, APIError, InvalidVersion
    from girder_worker.docker import nvidia
    from requests.exceptions import ReadTimeout
except ImportError:
    # These imports will not be available on the girder side.
    pass
from girder_worker.app import app, Task
from girder_worker import logger
from girder_worker.docker import utils
from girder_worker.docker.stream_adapter import DockerStreamPushAdapter
from girder_worker.docker.io import (
    FileDescriptorReader,
    FDWriteStreamConnector,
    FDReadStreamConnector,
    FDStreamConnector,
    StdStreamWriter
)
from girder_worker.docker.transforms import (
    ContainerStdErr,
    ContainerStdOut,
    _TemporaryVolumeBase,
    TemporaryVolume
)
from girder_worker.utils import _walk_obj


BLACKLISTED_DOCKER_RUN_ARGS = ['tty', 'detach', 'volumes']


def _pull_image(image):
    """
    Pulls the specified Docker image onto this worker.
    """
    client = docker.from_env(version='auto')
    try:
        client.images.pull(image)
    except DockerException:
        logger.exception('Error pulling Docker image %s:' % image)
        raise


def _get_docker_network():
    try:
        ip = socket.gethostbyname(socket.gethostname())
        if 'DOCKER_CLIENT_TIMEOUT' in os.environ:
            timeout = int(os.environ['DOCKER_CLIENT_TIMEOUT'])
            client = docker.from_env(version='auto', timeout=timeout)
        else:
            client = docker.from_env(version='auto')
        for container in client.containers.list(all=True, filters={'status': 'running'}):
            for nw in container.attrs['NetworkSettings']['Networks'].values():
                if nw['IPAddress'] == ip:
                    return 'container:%s' % container.id
    except Exception:
        logger.exception('Failed to get docker network')


def _remove_stopped_container(client, name):
    if name is None:
        return
    for container in client.containers.list(all=True, filters={'name': name}):
        try:
            logger.info('Removing container %s ' % (name))
            container.remove()
        except Exception:
            pass


def _run_container(image, container_args, **kwargs):
    # TODO we could allow configuration of non default socket
    if 'DOCKER_CLIENT_TIMEOUT' in os.environ:
        timeout = int(os.environ['DOCKER_CLIENT_TIMEOUT'])
        client = docker.from_env(version='auto', timeout=timeout)
    else:
        client = docker.from_env(version='auto')

    runtime = kwargs.pop('runtime', None)
    origRuntime = runtime
    if runtime is None and nvidia.is_nvidia_image(client.api, image):
        runtime = 'nvidia'

    container_args = [str(arg) for arg in container_args]

    if 'network' not in kwargs and 'network_mode' not in kwargs:
        docker_network = _get_docker_network()
        if docker_network:
            kwargs = kwargs.copy()
            kwargs['network'] = docker_network

    logger.info('Running container: image: %s args: %s runtime: %s kwargs: %s'
                % (image, container_args, runtime, kwargs))
    try:
        name = None
        try:
            if runtime == 'nvidia' and kwargs.get('device_requests') is None:
                # Docker < 19.03 required the runtime='nvidia' argument.
                # Newer versions require a device request for some number of
                # GPUs.  This should handle either version of the docker
                # daemon.
                try:
                    device_requests_kwargs = kwargs.copy()
                    device_requests_kwargs['device_requests'] = [
                        docker.types.DeviceRequest(count=-1, capabilities=[['gpu']])]
                    name = device_requests_kwargs.setdefault(
                        'name',
                        'girder_worker_' + datetime.datetime.now().strftime('%Y%m%d_%H%M%S_%f'))
                    return client.containers.run(
                        image, container_args, **device_requests_kwargs)
                except (APIError, InvalidVersion):
                    _remove_stopped_container(client, name)
                    pass
            kwargs = kwargs.copy()
            name = kwargs.setdefault(
                'name',
                'girder_worker_' + datetime.datetime.now().strftime('%Y%m%d_%H%M%S_%f'))
            return client.containers.run(
                image, container_args, runtime=runtime, **kwargs)
        except APIError:
            _remove_stopped_container(client, name)
            if origRuntime is None and runtime is not None:
                kwargs = kwargs.copy()
                name = kwargs.setdefault(
                    'name',
                    'girder_worker_' + datetime.datetime.now().strftime('%Y%m%d_%H%M%S_%f'))
                return client.containers.run(image, container_args, **kwargs)
            else:
                raise
    except DockerException:
        logger.exception('Exception when running docker container')
        raise


class _SocketReader(FileDescriptorReader):
    """
    Used to mediate the difference between the python 2/3 implementation of docker-py
    with python 2 attach_socket(...) returns a socket like object, with python 3
    it returns an instance of SocketIO.
    """

    def __init__(self, socket):
        self._socket = socket

    def read(self, n):
        # socket
        if hasattr(self._socket, 'recv'):
            return self._socket.recv(n)

        # SocketIO
        return self._socket.read(n)

    def fileno(self):
        return self._socket.fileno()

    def close(self):
        self._socket.close()


def _run_select_loop(  # noqa: C901
        task, container, read_stream_connectors, write_stream_connectors):
    stdout = None
    stderr = None
    try:
        # attach to standard streams
        stdout = container.attach_socket(params={
            'stdout': True,
            'logs': True,
            'stream': True
        })

        stderr = container.attach_socket(params={
            'stderr': True,
            'logs': True,
            'stream': True
        })

        def exit_condition():
            container.reload()
            return container.status in {'exited', 'dead'} or task.canceled

        # Look for ContainerStdOut and ContainerStdErr instances that need
        # to be replace with the real container streams.
        stdout_connected = False
        for read_stream_connector in read_stream_connectors:
            if isinstance(read_stream_connector.input, ContainerStdOut):
                stdout_reader = _SocketReader(stdout)
                read_stream_connector.output = DockerStreamPushAdapter(read_stream_connector.output)
                read_stream_connector.input = stdout_reader
                stdout_connected = True
                break

        stderr_connected = False
        for read_stream_connector in read_stream_connectors:
            if isinstance(read_stream_connector.input, ContainerStdErr):
                stderr_reader = _SocketReader(stderr)
                read_stream_connector.output = DockerStreamPushAdapter(read_stream_connector.output)
                read_stream_connector.input = stderr_reader
                stderr_connected = True
                break

        # If not stdout and stderr connection has been provided just use
        # sys.stdXXX
        if not stdout_connected:
            stdout_reader = _SocketReader(stdout)
            connector = FDReadStreamConnector(
                stdout_reader,
                DockerStreamPushAdapter(StdStreamWriter(sys.stdout)))
            read_stream_connectors.append(connector)

        if not stderr_connected:
            stderr_reader = _SocketReader(stderr)
            connector = FDReadStreamConnector(
                stderr_reader,
                DockerStreamPushAdapter(StdStreamWriter(sys.stderr)))
            read_stream_connectors.append(connector)

        # Run select loop
        utils.select_loop(exit_condition=exit_condition,
                          readers=read_stream_connectors,
                          writers=write_stream_connectors)

        if task.canceled:
            try:
                msg = 'Asking to stop container: %s' % container.id
                logger.info(msg)
                container.stop()
            # Catch the ReadTimeout from requests and wait for container to
            # exit. See https://github.com/docker/docker-py/issues/1374 for
            # more details.
            except ReadTimeout:
                tries = 10
                while tries > 0:
                    container.reload()
                    if container.status == 'exited':
                        break
                    tries -= 1
                    time.sleep(1)

                if container.status != 'exited':
                    msg = 'Unable to stop container: %s' % container.id
                    logger.error(msg)
            except DockerException as dex:
                logger.error(dex)
                raise

        container.reload()
        exit_code = container.attrs['State']['ExitCode']
        if not task.canceled and exit_code != 0:
            raise DockerException('Non-zero exit code from docker container (%d).' % exit_code)
    finally:
        # Close our stdout and stderr sockets
        if stdout:
            stdout.close()
        if stderr:
            stderr.close()


def _handle_streaming_args(args):
    processed_args = []
    write_streams = []
    read_streams = []

    def _maybe_path(arg):
        if hasattr(arg, 'path'):
            return arg.path()

        # Don't pass anything
        return ''

    for arg in args:
        if isinstance(arg, FDStreamConnector):
            if isinstance(arg, FDWriteStreamConnector):
                write_streams.append(arg)
                arg = _maybe_path(arg.output)

            elif isinstance(arg, FDReadStreamConnector):
                read_streams.append(arg)
                arg = _maybe_path(arg.input)

        processed_args.append(arg)

    return (processed_args, read_streams, write_streams)


class _RequestDefaultTemporaryVolume(_TemporaryVolumeBase):
    def __init__(self):
        super().__init__(None, None)
        self._make_paths()

    def transform(self, **kwargs):
        self._transformed = True


class DockerTask(Task):

    def _maybe_transform_argument(self, arg):
        return super()._maybe_transform_argument(
            arg, task=self, _default_temp_volume=self.request._default_temp_volume)

    def _maybe_transform_result(self, idx, result):
        return super()._maybe_transform_result(
            idx, result, _default_temp_volume=self.request._default_temp_volume)

    def __call__(self, *args, **kwargs):
        default_temp_volume = _RequestDefaultTemporaryVolume()
        self.request._default_temp_volume = default_temp_volume

        volumes = kwargs.setdefault('volumes', {})
        # If we have a list of volumes, the user provide a list of Volume objects,
        # we need to transform them.
        temp_volumes = []
        if isinstance(volumes, list):
            # See if we have been passed any TemporaryVolume instances.
            for v in volumes:
                if isinstance(v, TemporaryVolume):
                    temp_volumes.append(v)

            # First call the transform method, this we replace default temp volumes
            # with the instance associated with this task create above. That is any
            # reference to TemporaryVolume.default
            _walk_obj(volumes, self._maybe_transform_argument)

            # Now convert them to JSON
            def _json(volume):
                return volume._repr_json_()

            volumes = _walk_obj(volumes, _json)
            # We then need to merge them into a single dict and it will be ready
            # for docker-py.
            volumes = {k: v for volume in volumes for k, v in volume.items()}
            kwargs['volumes'] = volumes

        volumes.update(default_temp_volume._repr_json_())

        try:
            super().__call__(*args, **kwargs)
        finally:
            threading.Thread(
                target=self._cleanup_temp_volumes,
                args=(temp_volumes, default_temp_volume),
                daemon=True).start()

    def _cleanup_temp_volumes(self, temp_volumes, default_temp_volume):
        # Set the permission to allow cleanup of temp directories
        temp_volumes = [v for v in temp_volumes if os.path.exists(v.host_path)]
        to_chmod = temp_volumes[:]
        # If our default_temp_volume instance has been transformed then we
        # know it has been used and we have to clean it up.
        if default_temp_volume._transformed:
            to_chmod.append(default_temp_volume)
            temp_volumes.append(default_temp_volume)

        if len(to_chmod) > 0:
            utils.chmod_writable([v.host_path for v in to_chmod])

        for v in temp_volumes:
            shutil.rmtree(v.host_path)


def _add_environment_kargs(run_kwargs):
    envkey = 'GIRDER_WORKER_DOCKER_RUN_OPTIONS'
    if envkey not in os.environ:
        return
    try:
        opts = json.loads(os.environ[envkey])
        extra_run_kwargs = {k: v for k, v in opts.items() if k not in BLACKLISTED_DOCKER_RUN_ARGS}
        run_kwargs.update(extra_run_kwargs)
        if 'volumes' in opts:
            if isinstance(opts['volumes'], list):
                opts['volumes'] = {
                    v.split(':')[0]: {
                        'bind': v.split(':')[1],
                        'mode': (v + ':ro').split(':')[2]}
                    for v in opts['volumes']}
            if 'volumes' not in run_kwargs:
                run_kwargs['volumes'] = {}
            run_kwargs['volumes'].update(opts['volumes'])
    except Exception:
        logger.exception(f'Failed to parse {envkey}')


def _docker_run(task, image, pull_image=True, entrypoint=None, container_args=None,
                volumes=None, remove_container=True, stream_connectors=None, **kwargs):
    volumes = volumes or {}
    stream_connectors = stream_connectors or []
    container_args = container_args or []

    if pull_image:
        logger.info('Pulling Docker image: %s', image)
        _pull_image(image)

    if entrypoint is not None and not isinstance(entrypoint, (list, tuple)):
        entrypoint = [entrypoint]

    run_kwargs = {
        'tty': False,
        'volumes': volumes,
        'detach': True
    }
    _add_environment_kargs(run_kwargs)

    # Allow run args to be overridden,filter out any we don't want to override
    extra_run_kwargs = {k: v for k, v in kwargs.items() if k not in BLACKLISTED_DOCKER_RUN_ARGS}
    run_kwargs.update(extra_run_kwargs)

    if entrypoint is not None:
        run_kwargs['entrypoint'] = entrypoint

    container_args, read_streams, write_streams = _handle_streaming_args(container_args)

    for connector in stream_connectors:
        if isinstance(connector, FDReadStreamConnector):
            read_streams.append(connector)
        elif isinstance(connector, FDWriteStreamConnector):
            write_streams.append(connector)
        else:
            raise TypeError(
                "Expected 'FDReadStreamConnector' or 'FDWriterStreamConnector', received '%s'"
                % type(connector))

    # We need to open any read streams before starting the container, so the
    # underling named pipes are opened for read.
    for stream in read_streams:
        stream.open()

    container = _run_container(image, container_args, **run_kwargs)
    try:
        _run_select_loop(task, container, read_streams, write_streams)
    finally:
        if container and remove_container:
            container.reload()
            # If the container is still running issue a warning
            if container.status == 'running':
                logger.warning('Container is still running, unable to remove.')
            else:
                container.remove()

    # return an array of None's equal to number of entries in the girder_result_hooks
    # header, in order to trigger processing of the container outputs.
    results = []
    if hasattr(task.request, 'girder_result_hooks'):
        results = (None,) * len(task.request.girder_result_hooks)

    return results


@app.task(base=DockerTask, bind=True)
def docker_run(task, image, pull_image=True, entrypoint=None, container_args=None,
               volumes=None, remove_container=True, **kwargs):
    """
    This task runs a docker container. For details on how to use this task, see the
    :ref:`docker-run` guide.

    :param task: The bound task reference.
    :type task: :py:class:`girder_worker.task.Task`
    :param image: The docker image identifier.
    :type image: str
    :param pull_image: Whether to explicitly pull the image prior to running the container.
    :type pull_image: bool
    :param entrypoint: Alternative entrypoint to use when running the container.
    :type entrypoint: str
    :param container_args: Arguments to pass to the container.
    :type container_args: list
    :param volumes: Volumes to expose to the container.
    :type volumes: dict
    :param remove_container: Whether to delete the container after the task is done.
    :type remove_container: bool
    :return: Fulfilled result hooks.
    :rtype: list
    """
    return _docker_run(
        task, image, pull_image, entrypoint, container_args, volumes,
        remove_container, **kwargs)
