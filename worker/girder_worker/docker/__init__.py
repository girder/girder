from girder_worker import GirderWorkerPluginABC


class DockerPlugin(GirderWorkerPluginABC):

    def __init__(self, app, *args, **kwargs):
        self.app = app

    def task_imports(self):
        return ['girder_worker.docker.tasks']
