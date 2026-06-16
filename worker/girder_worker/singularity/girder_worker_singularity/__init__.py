from girder_worker import GirderWorkerPluginABC


class SingularityPlugin(GirderWorkerPluginABC):

    def __init__(self, app, *args, **kwargs):
        self.app = app

    def task_imports(self):
        return ['girder_worker.singularity.girder_worker_singularity.tasks']
