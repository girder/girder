from girder_worker import GirderWorkerPluginABC


class CoreWorkerPlugin(GirderWorkerPluginABC):
    def __init__(self, app, *args, **kwargs):
        self.app = app

    def task_imports(self):
        return ['girder.tasks']
