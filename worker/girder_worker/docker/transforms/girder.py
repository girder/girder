import errno
import os
import shutil
from girder_worker.utils.transform import Transform
from girder_worker.utils.transforms.girder_io import (
    GirderUploadJobArtifact,
    GirderClientTransform,
    GirderUploadToFolder,
    GirderUploadToItem
)
from . import TemporaryVolume, Connect, NamedOutputPipe, _maybe_transform


def setPermissions(path, dirmode=0o777, filemode=0o644):
    """
    Set permissions on download assets so that workers can have full read
    access to them regardless of user.  For directories, they have full general
    access.
    """
    if os.path.isfile(path):
        try:
            os.chmod(path, filemode)
        except Exception:
            pass
    else:
        for dirpath, _, filenames in os.walk(path):
            try:
                os.chmod(dirpath, dirmode)
            except Exception:
                pass
            for filename in filenames:
                try:
                    os.chmod(os.path.join(dirpath, filename), filemode)
                except Exception:
                    pass


class ProgressPipe(Transform):
    """
    This can be used to stream progress information out of a running docker container as
    part of a docker_run task. For a usage example, see :ref:`docker-progress`.

    :param name: The filename, which will be a named pipe open for reading from the host.
    :type name: str
    :param volume: The bind mount volume where the underlying named pipe will reside.
    :type volume: :py:class:`girder_worker.docker.transforms.BindMountVolume`
    """

    def __init__(self, name='.girder_progress', volume=TemporaryVolume.default):
        self.name = name
        self._volume = volume

    def transform(self, task=None, **kwargs):
        from girder_worker.docker.stream_adapter import JobProgressAdapter

        self._volume.transform(**kwargs)

        # TODO What do we do is job_manager is None? When can it me None?
        job_mgr = task.job_manager
        # For now we are using JobProgressAdapter which is part of core, we should
        # probably add a copy to the docker package to break to reference to core.
        return Connect(NamedOutputPipe(self.name, volume=self._volume),
                       JobProgressAdapter(job_mgr)).transform(**kwargs)


class GirderFileIdToStream(GirderClientTransform):
    """
    This can be used to stream a Girder file into a docker container. See
    :ref:`docker-run-streaming-input` for example usage.

    :param _id: The Girder file ID.
    :type _id: str or ObjectId
    """

    def __init__(self, _id, **kwargs):
        super().__init__(**kwargs)
        self.file_id = _id

    def transform(self, **kwargs):
        from girder_worker.docker.io.girder import (
            GirderFileStreamReader
        )
        return GirderFileStreamReader(self.gc, self.file_id)


class GirderFileIdToVolume(GirderClientTransform):
    """
    This can be used to pass a Girder file into a docker container. It downloads
    the file to a bind mounted volume, and returns the container path of the file.

    :param _id: The Girder file ID.
    :type _id: str or ObjectId
    :param volume: The bind mount volume where the file will reside.
    :type volume: :py:class:`girder_worker.docker.transforms.BindMountVolume`
    :param filename: Alternate name for the file. Default is to use the name from Girder.
    :type filename: str
    """

    def __init__(self, _id, volume=TemporaryVolume.default, filename=None, **kwargs):
        super().__init__(**kwargs)
        self._file_id = str(_id)
        self._volume = volume
        self._filename = filename
        self._file_path = None

    def _create_file_path(self, root):
        if self._filename is None:
            # If no filename is explicitly passed, we read the filename from Girder
            # and put it in its own directory named by its UUID.
            filename = self.gc.getFile(self._file_id)['name']
            path = os.path.join(root, self._file_id)
            try:
                os.mkdir(path)
            except OSError as e:
                if e.errno != errno.EEXIST:
                    raise

            return os.path.join(self._file_id, filename), os.path.join(path, filename)
        else:
            return self._filename, os.path.join(root, self._filename)

    def transform(self, **kwargs):
        self._volume.transform(**kwargs)
        dir = self._volume.host_path
        rel_path, self._file_path = self._create_file_path(dir)

        self.gc.downloadFile(self._file_id, self._file_path)
        setPermissions(self._file_path)

        # Return the path inside the container
        return os.path.join(self._volume.container_path, rel_path)

    def cleanup(self, **kwargs):
        if self._file_path is not None:
            shutil.rmtree(self._file_path, ignore_errors=True)

    def _repr_model_(self):
        if self._filename:
            template = '<{module}.{cls}: File ID={id} -> "{fname}">'
        else:
            template = '<{module}.{cls}: File ID={id}>'
        return template.format(
            module=self.__module__, cls=self.__class__.__name__, id=self._file_id,
            fname=self._filename)


class GirderFolderIdToVolume(GirderClientTransform):
    """
    This can be used to pass a Girder folder into a docker container. It downloads
    the folder to a bind mounted volume, and returns the container path of the directory.

    :param _id: The Girder folder ID.
    :type _id: str or ObjectId
    :param volume: The bind mount volume where the directory will reside.
    :type volume: :py:class:`girder_worker.docker.transforms.BindMountVolume`
    :param folder_name: Alternate name for the directory. Default is to use the name from Girder.
    :type folder_name: str
    """

    def __init__(self, _id, volume=TemporaryVolume.default, folder_name=None, **kwargs):
        super().__init__(**kwargs)
        self._folder_id = str(_id)
        self._volume = volume
        self._folder_name = folder_name
        self._folder_path = None

    def _create_folder_path(self, root):
        if self._folder_name is None:
            # If no folder name is explicitly passed, we read the filename from Girder
            # and put it in its own directory named by its UUID.
            self._folder_name = self.gc.getFolder(self._folder_id)['name']
        path = os.path.join(root, self._folder_id, self._folder_name)
        try:
            os.makedirs(path)
        except OSError as e:
            if e.errno != errno.EEXIST:
                raise

        return os.path.join(self._folder_id, self._folder_name), path

    def transform(self, **kwargs):
        self._volume.transform(**kwargs)
        dir = self._volume.host_path
        rel_path, self._folder_path = self._create_folder_path(dir)

        self.gc.downloadFolderRecursive(self._folder_id, self._folder_path)
        setPermissions(self._folder_path)

        # Return the path inside the container
        return os.path.join(self._volume.container_path, rel_path)

    def cleanup(self, **kwargs):
        if self._folder_path is not None:
            shutil.rmtree(self._folder_path, ignore_errors=True)

    def _repr_model_(self):
        return '<%s.%s: Folder ID=%s -> "%s">' % (
            self.__module__, self.__class__.__name__, self._folder_id, self._folder_path)


class GirderItemIdToVolume(GirderClientTransform):
    """
    This can be used to pass a Girder item into a docker container. It downloads
    the item to a bind mounted volume, and returns the container path of the directory.

    :param _id: The Girder item ID.
    :type _id: str or ObjectId
    :param volume: The bind mount volume where the item will reside.
    :type volume: :py:class:`girder_worker.docker.transforms.BindMountVolume`
    :param item_name: Alternate name for the file. Default is to use the name from Girder.
    :type item_name: str
    """

    def __init__(self, _id, volume=TemporaryVolume.default, **kwargs):
        super().__init__(**kwargs)
        self._item_id = str(_id)
        self._volume = volume
        self._item_path = None

    def _create_item_path(self, root):
        path = os.path.join(root, self._item_id)
        try:
            os.makedirs(path)
        except OSError as e:
            if e.errno != errno.EEXIST:
                raise

        return self._item_id, path

    def transform(self, **kwargs):
        self._volume.transform(**kwargs)
        rel_path, self._item_path = self._create_item_path(self._volume.host_path)

        self.gc.downloadItem(self._item_id, self._item_path)
        setPermissions(self._item_path)

        # downloadItem always puts the item underneath the dest at its transformed name,
        # so we find where it placed it with listdir
        rel_path = os.path.join(rel_path, os.listdir(self._item_path)[0])

        # Return the path inside the container
        return os.path.join(self._volume.container_path, rel_path)

    def cleanup(self, **kwargs):
        if self._item_path is not None:
            shutil.rmtree(self._item_path, ignore_errors=True)

    def _repr_model_(self):
        return '<%s.%s: Item ID=%s -> "%s">' % (
            self.__module__, self.__class__.__name__, self._item_id, self._item_path)


class GirderUploadVolumePathToItem(GirderUploadToItem):
    """
    This transform uploads data in a bind mount volume to a Girder item. This should be used
    in ``girder_result_hooks`` to upload files produced by the task.

    :param volumepath: The location of the file to upload.
    :type volumepath: :py:class:`girder_worker.docker.transforms.VolumePath`
    :param item_id: The item ID in Girder.
    :type item_id: str or ObjectId
    :param delete_file: Whether to delete the file afterward.
    :type delete_file: bool
    """

    def __init__(self, volumepath, item_id, delete_file=False, **kwargs):
        item_id = str(item_id)
        super().__init__(item_id, delete_file, **kwargs)
        self._volumepath = volumepath

    # We ignore the "result"
    def transform(self, *args, **kwargs):
        path = _maybe_transform(self._volumepath, *args, **kwargs)

        return super().transform(path)


class GirderUploadVolumePathToFolder(GirderUploadToFolder):
    """
    This transform uploads data in a bind mount volume to a Girder folder. This should be used
    in ``girder_result_hooks`` to upload data produced by the task.

    :param volumepath: The location of the file or directory to upload.
    :type volumepath: :py:class:`girder_worker.docker.transforms.VolumePath`
    :param folder_id: The folder ID in Girder.
    :type folder_id: str or ObjectId
    :param delete_file: Whether to delete the data afterward.
    :type delete_file: bool
    """

    def __init__(self, volumepath, folder_id, delete_file=False, **kwargs):
        super().__init__(str(folder_id), delete_file, **kwargs)
        self._volumepath = volumepath

    def transform(self, *args, **kwargs):
        path = _maybe_transform(self._volumepath, *args, **kwargs)
        return super().transform(path)


class GirderUploadVolumePathJobArtifact(GirderUploadJobArtifact):
    """
    This transform can be used to upload artifacts produced during a docker task execution
    and attach them to the corresponding job in Girder. This can be useful for tracing and
    debugging jobs, or simply collecting intermediate information during job execution. If
    the passed in path does not exist, this is a no-op.

    :param volumepath: A volume path pointing to a mounted directory or file. If a directory,
        all files within the directory will be uploaded as artifacts to the job. If a file,
        just uploads the single file. If it does not exist, no action is performed.
    :type volumepath: :py:class:`girder_worker.docker.transforms.VolumePath`
    :param job_id: The job ID to attach the artifacts to. If calling this from Girder via
        ``docker_run.delay``, you will not need to set this, as it will be set automatically.
    :type job_id: str
    :param name: A name for the artifact. Only applies for single file paths. If not specified,
        will use the basename of the file.
    :type name: str
    :param upload_on_exception: If True, this transform will occur even if the docker task
        fails. This can be used to debug failed ``docker_run`` tasks.
    :type upload_on_exception: bool
    """

    def __init__(self, volumepath, job_id=None, name=None, upload_on_exception=False, **kwargs):
        if job_id is not None:
            job_id = str(job_id)
        super().__init__(job_id, name, **kwargs)
        self._volumepath = volumepath
        self._upload_on_exception = upload_on_exception

    def transform(self, *args, **kwargs):
        path = _maybe_transform(self._volumepath, *args, **kwargs)
        return super().transform(path)

    def exception(self):
        if self._upload_on_exception:
            return self.transform()
