import abc
import os
import stat
import sys
import tempfile
import uuid

from girder_worker.utils.transform import Transform

TEMP_VOLUME_MOUNT_PREFIX = '/mnt/girder_worker'


def _maybe_transform(obj, *args, **kwargs):
    if hasattr(obj, 'transform') and callable(obj.transform):
        return obj.transform(*args, **kwargs)

    return obj


class HostStdOut(Transform):
    """
    Represents the standard output stream on the host machine. Can be used with
    :py:class:`girder_worker.docker.transforms.Connect` to write text to stdout.
    """

    def transform(self, **kwargs):
        from girder_worker.docker.io import (
            StdStreamWriter
        )
        return StdStreamWriter(sys.stdout)


class HostStdErr(Transform):
    """
    Represents the standard error stream on the host machine. Can be used with
    :py:class:`girder_worker.docker.transforms.Connect` to write text to stderr.
    """

    def transform(self, **kwargs):
        from girder_worker.docker.io import (
            StdStreamWriter
        )
        return StdStreamWriter(sys.stderr)


class ContainerStdOut(Transform):
    """
    Represents the standard output stream of the container. Can be used with
    :py:class:`girder_worker.docker.transforms.Connect` to redirect the containers
    standard output to another stream.
    """

    def transform(self, **kwargs):
        return self

    def open(self):
        # noop
        pass


class ContainerStdErr(Transform):
    """
    Represents the standard error stream of the container. Can be used with
    :py:class:`girder_worker.docker.transforms.Connect` to redirect the containers
    standard error to another stream.
    """

    def transform(self, **kwargs):
        return self

    def open(self):
        # noop
        pass


class BindMountVolume(Transform):
    """
    A volume that will be bind mounted into a docker container.

    :param host_path: The path on the host machine.
    :type host_path: str
    :param container_path: The path in the container this volume will be mounted
        at.
    :type container_path: str
    :param mode: The mounting mode
    :type mode: str
    """

    def __init__(self, host_path, container_path, mode='rw'):
        self._host_path = host_path
        self._container_path = container_path
        self.mode = mode

    def _repr_json_(self):
        return {
            self.host_path: {
                'bind': self.container_path,
                'mode': self.mode
            }
        }

    def transform(self, **kwargs):
        return self.container_path

    @property
    def container_path(self):
        return self._container_path

    @property
    def host_path(self):
        return self._host_path


class _TemporaryVolumeMetaClass(abc.ABCMeta):
    @property
    def default(cls):
        """
        This returns the default temporary volume that is always mounted into the container.
        """
        return _DefaultTemporaryVolume()


class _TemporaryVolumeBase(BindMountVolume):
    def __init__(self, *arg, **kwargs):
        super().__init__(*arg, **kwargs)
        self._transformed = False

    def _make_paths(self, host_dir=None, mode=0o755):
        if host_dir is not None and not os.path.exists(host_dir):
            os.makedirs(host_dir)
            # Sometimes we need to explicitly set the mode of the
            # directory to 0o777 (e.g. when running the integration
            # tests). To do this explicitly (without the user's umask
            # getting in the way) we must make a separate call to
            # os.chmod.
            os.chmod(host_dir, mode)
        self._host_path = tempfile.mkdtemp(dir=host_dir)
        try:
            # this is permissive as a worker may be running as a different user
            # and could otherwise not read or create files.
            os.chmod(self._host_path, 0o777 | stat.S_ISGID)
        except Exception:
            pass
        self._container_path = os.path.join(TEMP_VOLUME_MOUNT_PREFIX, uuid.uuid4().hex)


class TemporaryVolume(_TemporaryVolumeBase, metaclass=_TemporaryVolumeMetaClass):
    """
    This is a class used to represent a temporary directory on the host that will
    be mounted into a docker container. girder_worker will automatically attach a default
    temporary volume. This can be reference using `TemporaryVolume.default` class attribute.
    A temporary volume can also be create in a particular host directory by providing the
    `host_dir` param.

    :param host_dir: The root directory on the host to use when creating the
        the temporary host path.
    :type host_dir: str
    :param mode: The default mode applied to the temporary volume if it does
        not already exist.
    :type mode: int
    """

    # Note that this mode is explicitly set with os.chmod. What you
    # set, is what you get - no os.makedirs umask shenanigans.

    def __init__(self, host_dir=None, mode=0o777):
        super().__init__(None, None)
        self.host_dir = host_dir
        self._mode = mode
        self._instance = None
        self._transformed = False

    def transform(self, **kwargs):
        if not self._transformed:
            self._transformed = True
            self._make_paths(self.host_dir, mode=self._mode)

        return super().transform(**kwargs)


class _DefaultTemporaryVolume(TemporaryVolume):
    """
    Place holder who delegates implementation to instance provide by transform(...) method
    An instance of the class is returned each time `TemporaryVolume.default` is accessed.
    When the docker_run task is executed the transform(...) method is call with an instance
    containing information about the actual default temporary volume associated with the
    task. The place holder then delegates all functionality to this instance.
    """

    def transform(self, _default_temp_volume=None, **kwargs):
        self._instance = _default_temp_volume
        self._transformed = True

        return self._instance.transform(**kwargs)

    @property
    def container_path(self):
        return self._instance.container_path

    @property
    def host_path(self):
        return self._instance.host_path


class NamedPipeBase(Transform):
    def __init__(self, name, container_path=None, host_path=None, volume=TemporaryVolume.default):
        super().__init__()
        self._container_path = None
        self._host_path = None
        self._volume = None

        if container_path is not None and host_path is not None:
            self._container_path = container_path
            self._host_path = host_path
        else:
            self._volume = volume

        self.name = name

    def transform(self, **kwargs):
        if self._volume is not None:
            self._volume.transform(**kwargs)

    @property
    def container_path(self):
        """
        The path within the docker container.
        """
        if self._container_path is not None:
            return os.path.join(self._container_path, self.name)
        else:
            return os.path.join(self._volume.container_path, self.name)

    @property
    def host_path(self):
        """
        The path on the host machine
        """
        if self._host_path is not None:
            return os.path.join(self._host_path, self.name)
        else:
            return os.path.join(self._volume.host_path, self.name)

    def cleanup(self, **kwargs):
        os.remove(self.host_path)


class NamedInputPipe(NamedPipeBase):
    """
    A named pipe that can be open for read within a docker container.
    i.e. To stream data into a container.

    :param name: The name of the pipe.
    :type name: str
    :param container_path: The path in the container.
    :type container_path: str
    :param host_path: The path on the host machine.
    :type host_path: str
    :param volume: Alternatively a :py:class:`girder_worker.docker.transforms.BindMountVolume`
        instance can be provided. In which case the container_path and host_paths from
        the volume will be used when creating the pipe. The default location is
        :py:obj:`girder_worker.docker.transforms.TemporaryVolume.default`
    """

    def __init__(self, name, container_path=None, host_path=None, volume=TemporaryVolume.default):
        super().__init__(name, container_path, host_path, volume)

    def transform(self, **kwargs):
        from girder_worker.docker.io import (
            NamedPipe,
            NamedPipeWriter
        )
        super().transform(**kwargs)

        pipe = NamedPipe(self.host_path)
        return NamedPipeWriter(pipe, self.container_path)


class NamedOutputPipe(NamedPipeBase):
    """
    A named pipe that can be opened for write within a docker container.
    i.e. To stream data out of a container.

    :param name: The name of the pipe.
    :type name: str
    :param container_path: The path in the container.
    :type container_path: str
    :param host_path: The path on the host machine.
    :type host_path: str
    :param volume: Alternatively a :py:class:`girder_worker.docker.transforms.BindMountVolume`
        instance can be provided. In which can the container_path and host_paths from
        the volume will be use when creating the pipe. The default location is
        :py:attr:`girder_worker.docker.transforms.TemporaryVolume.default`
    """

    def __init__(self, name, container_path=None, host_path=None, volume=TemporaryVolume.default):
        super().__init__(name, container_path, host_path, volume)

    def transform(self, **kwargs):
        from girder_worker.docker.io import (
            NamedPipe,
            NamedPipeReader
        )
        super().transform(**kwargs)

        pipe = NamedPipe(self.host_path)
        return NamedPipeReader(pipe, self.container_path)


class VolumePath(Transform):
    """
    A path on a docker volume. Must be a path relative to the root of the volume.

    :param filename: The file name.
    :type name: str
    :param volume: The volume this file lived on. If no volume is provided then
        the file will be on
        :py:attr:`girder_worker.docker.transforms.TemporaryVolume.default`
    :type volume: :py:class:`girder_worker.docker.transforms.BindMountVolume`
    """

    def __init__(self, filename, volume=TemporaryVolume.default):
        if os.path.isabs(filename):
            raise Exception('VolumePath paths must be relative to a volume (%s).' % filename)

        self.filename = filename
        self._volume = volume

    def transform(self, *pargs, **kwargs):
        self._volume.transform(**kwargs)
        # If we are being called with arguments, then this is the execution of
        # girder_result_hooks, so return the host_path
        if len(pargs) > 0:
            return os.path.join(self._volume.host_path, self.filename)
        else:
            return os.path.join(self._volume.container_path, self.filename)

    def _repr_model_(self):
        return '<%s.%s: "%s">' % (self.__module__, self.__class__.__name__, self.filename)


class Connect(Transform):
    """
    This utility class represents the connection between a
    :py:class:`girder_worker.docker.transforms.NamedOutputPipe` or
    :py:class:`girder_worker.docker.transforms.NamedInputPipe` and one of the other streaming
    transforms. Girder Worker will stream the data to or from the named pipe.

    :param input: The input side of the connection
    :type input: :py:class:`girder_worker.docker.transforms.NamedOutputPipe` or
        :py:class:`girder_worker.docker.transforms.girder.GirderFileIdToStream`
    :param output: The output side of the connection
    :type output: :py:class:`girder_worker.docker.transforms.NamedInputPipe` or
        :py:class:`girder_worker.docker.transforms.ChunkedTransferEncodingStream` or
        :py:class:`girder_worker.docker.transforms.HostStdOut` or
        :py:class:`girder_worker.docker.transforms.HostStdErr`
    """

    def __init__(self, input, output):
        super().__init__()
        self._input = input
        self._output = output

    def transform(self, **kwargs):
        from girder_worker.docker.io import (
            FDWriteStreamConnector,
            FDReadStreamConnector,
        )
        input = _maybe_transform(self._input, **kwargs)
        output = _maybe_transform(self._output, **kwargs)
        if isinstance(self._output, NamedInputPipe):
            return FDWriteStreamConnector(input, output)
        elif isinstance(self._input, NamedOutputPipe):
            return FDReadStreamConnector(input, output)
        else:
            raise TypeError('A NamedInputPipe or NamedOutputPipe must be provided.')

    def _repr_model_(self):
        """
        The method is called before save the argument in the job model.
        """
        return str(self)


class ChunkedTransferEncodingStream(Transform):
    """
    A stream transform that allows data to be streamed using HTTP Chunked Transfer Encoding
    to a server.

    :param url: Destination URL for the stream.
    :type url: str
    :param headers: HTTP headers to send.
    :type header: dict
    """

    def __init__(self, url, headers=None, **kwargs):
        self.url = url
        self.headers = headers or {}

    def transform(self, **kwargs):
        from girder_worker.docker.io import (
            ChunkedTransferEncodingStreamWriter
        )

        return ChunkedTransferEncodingStreamWriter(self.url, self.headers)
