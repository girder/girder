import os
import shutil
import tempfile

from ..girder_io import GirderClientTransform


class GirderFileIdAllowDirect(GirderClientTransform):
    """
    This transform either uses direct path to access a file, if possible and
    allowed, or downloads a Girder File to the local machine and passes its
    local path into the function.  The direct path is only used if the
    GW_DIRECT_PATHS environment variable is set.

    WARNING: if a direct path is used, the task MUST NOT modify the file.  It
    is the resposibility of the user of this transform to ensure tasks treat
    files as read-only.

    To use this transform from Girder, it should be called via something like:
    ```
    try:
        local_path = File().getLocalFilePath(file)
    except FilePathException:
        local_path = None
    input_path = GirderFileIdAllowDirect(
        str(file['_id']), file['name'], local_path)
    ```

    :param _id: The ID of the file to download.
    :type _id: str
    :param name: The name of the file.  If the file must be downloaded, the
        extension is preserved.
    :type name: str
    :param local_path: If specified and the path exists and is reachable by
        after the transform, the file is accessed directly.
    :type local_path: str
    """

    def __init__(self, _id, name='', local_path=None, **kwargs):
        super().__init__(**kwargs)
        self.file_id = _id
        self.file_name = name
        self.local_file_path = local_path

    def _repr_model_(self):
        if self.local_file_path:
            return '{}({!r}, {!r}, {!r})'.format(
                self.__class__.__name__, self.file_id, self.file_name, self.local_file_path)
        return f'{self.__class__.__name__}({self.file_id!r}, {self.file_name!r})'

    def _allowDirectPath(self):
        """
        Check if the worker environment permits direct paths.  This just checks
        if the environment variable GW_DIRECT_PATHS is set to a non-empty
        value.

        :returns: True if direct paths are allowed.
        """
        return bool(os.environ.get('GW_DIRECT_PATHS'))

    def transform(self):
        # Don't download if self.local_file_path is set and direct paths are
        # allowed.
        if (self.local_file_path and self._allowDirectPath()
                and os.path.isfile(self.local_file_path)):
            self.temp_dir_path = None
            self.file_path = self.local_file_path
        else:
            self.temp_dir_path = tempfile.mkdtemp()
            self.file_path = os.path.join(self.temp_dir_path, '{}{}'.format(
                self.file_id, os.path.splitext(self.file_name)[1]))
            self.gc.downloadFile(self.file_id, self.file_path)
        return self.file_path

    def cleanup(self):
        if self.temp_dir_path:
            shutil.rmtree(self.temp_dir_path, ignore_errors=True)
