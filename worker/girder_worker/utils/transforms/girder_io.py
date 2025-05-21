import mimetypes
import os
import shutil
import tempfile

from girder_client import GirderClient
from urllib.parse import urlencode

from ..transform import ResultTransform, Transform


class GirderClientTransform(Transform):
    def __init__(self, *args, **kwargs):  # noqa
        gc = kwargs.pop('gc', None)

        try:
            if gc is None:
                # We need to resolve Girder's API URL, but girder_worker can
                # specify a different value than what Girder gets from a rest
                # request.
                from girder_plugin_worker.utils import getWorkerApiUrl
                self.gc = GirderClient(apiUrl=getWorkerApiUrl())
                from girder.api.rest import getCurrentUser
                if getCurrentUser():
                    from girder.constants import TokenScope
                    from girder.models.token import Token
                    scope = [TokenScope.DATA_READ, TokenScope.DATA_WRITE]
                    if 'GIRDER_WORKER_JOB_GC_SCOPE' in os.environ:
                        try:
                            scope = list({
                                part.strip('"[\'] ') for part in
                                os.environ['GIRDER_WORKER_JOB_GC_SCOPE'].split(',')} | set(scope))
                        except Exception:
                            pass
                    token = Token().createToken(
                        days=7,
                        scope=scope,
                        user=getCurrentUser(),
                    )['_id']
                else:
                    from girder.api.rest import getCurrentToken
                    token = getCurrentToken()['_id']
                self.gc.token = token
            else:
                self.gc = gc
        except ImportError:
            self.gc = None


class GirderClientResultTransform(ResultTransform, GirderClientTransform):
    pass


class GirderFileId(GirderClientTransform):
    """
    This transform downloads a Girder File to the local machine and passes its
    local path into the function.

    :param _id: The ID of the file to download.
    :type _id: str
    """

    def __init__(self, _id, **kwargs):
        super().__init__(**kwargs)
        self.file_id = _id

    def _repr_model_(self):
        return f"{self.__class__.__name__}('{self.file_id}')"

    def transform(self):
        self.file_path = os.path.join(
            tempfile.mkdtemp(), f'{self.file_id}')

        self.gc.downloadFile(self.file_id, self.file_path)

        return self.file_path

    def cleanup(self):
        if hasattr(self, 'file_path'):
            shutil.rmtree(os.path.dirname(self.file_path),
                          ignore_errors=True)


class GirderItemId(GirderClientTransform):
    """
    This transform downloads a Girder Item to a directory on the local machine
    and passes its local path into the function.

    :param _id: The ID of the item to download.
    :type _id: str
    """

    def __init__(self, _id, **kwargs):
        super().__init__(**kwargs)
        self.item_id = _id

    def _repr_model_(self):
        return f"{self.__class__.__name__}('{self.item_id}')"

    def transform(self):
        temp_dir = tempfile.mkdtemp()
        self.item_path = os.path.join(temp_dir, self.item_id)
        # os.mkdir(self.item_path)

        self.gc.downloadItem(self.item_id, temp_dir, self.item_id)

        return self.item_path

    def cleanup(self):
        if hasattr(self, 'item_path'):
            shutil.rmtree(os.path.dirname(self.item_path),
                          ignore_errors=True)


class GirderItemMetadata(GirderClientTransform):
    def __init__(self, _id, **kwargs):
        super().__init__(**kwargs)
        self.item_id = _id

    def _repr_model_(self):
        return f"{self.__class__.__name__}('{self.item_id}')"

    def transform(self, data):
        self.gc.addMetadataToItem(self.item_id, data)

        return data


class GirderUploadToItem(GirderClientResultTransform):
    """
    This is a result hook transform that uploads a file or flat directory of files
    to an item in Girder.

    :param _id: The ID of the item to upload into.
    :type _id: str
    :param delete_file: Whether to delete the local data afterward
    :type delete_file: bool
    :param upload_kwargs: Additional kwargs to pass to the upload method.
    :type upload_kwargs: dict
    """

    def __init__(self, _id, delete_file=False, upload_kwargs=None, **kwargs):
        super().__init__(**kwargs)
        self.item_id = _id
        self.upload_kwargs = upload_kwargs or {}
        self.delete_file = delete_file

    def _repr_model_(self):
        return f"{self.__class__.__name__}('{self.item_id}')"

    def transform(self, path):
        self.output_file_path = path
        if os.path.isdir(path):
            for f in os.listdir(path):
                f = os.path.join(path, f)
                if os.path.isfile(f):
                    self.gc.uploadFileToItem(self.item_id, f, **self.upload_kwargs)
        else:
            self.gc.uploadFileToItem(self.item_id, path, **self.upload_kwargs)
        return self.item_id

    def cleanup(self):
        if self.delete_file is True and hasattr(self, 'output_file_path'):
            if os.path.isdir(self.output_file_path):
                shutil.rmtree(self.output_file_path)
            else:
                os.remove(self.output_file_path)


class GirderUploadToFolder(GirderClientResultTransform):
    """
    This is a result hook transform that uploads a file or directory recursively
    to a folder in Girder.

    :param _id: The ID of the folder to upload into.
    :type _id: str
    :param delete_file: Whether to delete the local data afterward
    :type delete_file: bool
    :param upload_kwargs: Additional kwargs to pass to the upload method.
    :type upload_kwargs: dict
    """

    def __init__(self, _id, delete_file=False, upload_kwargs=None, must_exist=True, **kwargs):
        super().__init__(**kwargs)
        self.folder_id = _id
        self.upload_kwargs = upload_kwargs or {}
        self.delete_file = delete_file
        self.must_exist = True

    def _repr_model_(self):
        return f"{self.__class__.__name__}('{self.folder_id}')"

    def _uploadFolder(self, path, folder_id):
        for f in os.listdir(path):
            fpath = os.path.join(path, f)
            if os.path.isfile(fpath):
                self.gc.uploadFileToFolder(folder_id, fpath, **self.upload_kwargs)
            elif os.path.isdir(fpath) and not os.path.islink(fpath):
                folder = self.gc.createFolder(folder_id, f, reuseExisting=True)
                self._uploadFolder(fpath, folder['_id'])

    def transform(self, path):
        self.output_file_path = path
        if not self.must_exist and not os.path.exists(path):
            return None
        if os.path.isdir(path):
            self._uploadFolder(path, self.folder_id)
        else:
            self.gc.uploadFileToFolder(self.folder_id, path, **self.upload_kwargs)
        return self.folder_id

    def cleanup(self):
        if self.delete_file is True and hasattr(self, 'output_file_path'):
            if os.path.isdir(self.output_file_path):
                shutil.rmtree(self.output_file_path)
            else:
                os.remove(self.output_file_path)


class GirderUploadJobArtifact(GirderClientResultTransform):
    """
    This class can be used to upload a directory of files or a single file
    as artifacts attached to a Girder job. These files are only uploaded
    if they exist, so this is an optional output.

    Currently, only a flat directory of files is supported; the transform does not
    recurse through nested directories, though that may change in the future.

    :param job_id: The ID of the job to attach the file(s) to.
    :type job_id: str or ObjectId
    :param name: Name for the artifact (only if it's a single file).
    :type name: str
    """

    def __init__(self, job_id=None, name=None, **kwargs):
        super().__init__(**kwargs)
        self.job_id = job_id
        self.name = name

    def _repr_model_(self):
        return f"{self.__class__.__name__}('{self.job_id}')"

    def _upload_artifact(self, file, name=None):
        qs = urlencode({
            'name': name or os.path.basename(file),
            'size': os.stat(file).st_size,
            'mimeType': mimetypes.guess_type(file)[0]
        })
        with open(file, 'rb') as fh:
            self.gc.post('job/%s/artifact?%s' % (self.job_id, qs), data=fh)

    def transform(self, path):
        if self.job_id is None:
            self.job_id = str(self.job['_id'])

        if os.path.isdir(path):
            for f in os.listdir(path):
                f = os.path.join(path, f)
                if os.path.isfile(f):
                    self._upload_artifact(f)
        elif os.path.isfile(path):
            self._upload_artifact(path, self.name)
