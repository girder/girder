from pkg_resources import DistributionNotFound, get_distribution

from . import log_utils

try:
    __version__ = get_distribution(__name__).version
except DistributionNotFound:
    # package is not installed
    pass


__license__ = 'Apache 2.0'


# Create and configure our logger
logger = log_utils.setupLogger()


class GirderWorkerPluginABC:
    """
    Abstract base class for Girder Worker plugins. Plugins must descend from this
    class; see the :ref:`plugins` section for more information.
    """

    def __init__(*args, **kwargs):
        pass

    def task_imports(self):
        """Plugins should override this method if they have tasks."""
        return []


class GirderWorkerPlugin(GirderWorkerPluginABC):

    def __init__(self, app, *args, **kwargs):
        self.app = app

    def task_imports(self):
        return ['girder_worker.tasks']
