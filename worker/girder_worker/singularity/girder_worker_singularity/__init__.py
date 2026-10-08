"""Singularity (apptainer) execution support for girder-worker.

Tasks are only registered when the ``GIRDER_WORKER_SINGULARITY_ENABLED``
environment variable is set on the worker process.
"""

import os

from girder_worker import GirderWorkerPluginABC

GIRDER_WORKER_SINGULARITY_ENV = 'GIRDER_WORKER_SINGULARITY_ENABLED'


def singularity_enabled():
    """
    Return True when singularity (apptainer) task execution is enabled via the
    ``GIRDER_WORKER_SINGULARITY_ENABLED`` environment variable. Import
    availability of this package alone does not enable the behavior.
    """
    return os.environ.get(GIRDER_WORKER_SINGULARITY_ENV, '').lower() not in (
        '', '0', 'false', 'no'
    )


class SingularityPlugin(GirderWorkerPluginABC):

    def __init__(self, app, *args, **kwargs):
        self.app = app

    def task_imports(self):
        if not singularity_enabled():
            return []
        return ['girder_worker.singularity.girder_worker_singularity.tasks']
