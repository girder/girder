import shutil
import tempfile

from ..transform import Transform


class TemporaryDirectory(Transform):
    """
    This transform returns a temporary directory that is removed on cleanup.
    """

    def _repr_model_(self):
        return self.__class__.__name__

    def transform(self):
        self.temp_dir_path = tempfile.mkdtemp()
        return self.temp_dir_path

    def cleanup(self):
        if hasattr(self, 'temp_dir_path'):
            shutil.rmtree(self.temp_dir_path, ignore_errors=True)
