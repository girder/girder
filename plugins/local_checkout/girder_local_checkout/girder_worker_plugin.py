from girder_worker import GirderWorkerPluginABC


class LocalCheckoutWorkerPlugin(GirderWorkerPluginABC):
    def __init__(self, app, *args, **kwargs):
        self.app = app

    def task_imports(self):
        return ['girder_local_checkout.tasks']
