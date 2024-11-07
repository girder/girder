from girder_worker import GirderWorkerPluginABC


class CommonTasksPlugin(GirderWorkerPluginABC):
    def __init__(self, app, *args, **kwargs):
        self.app = app

    def task_imports(self):
        # Return a list of python importable paths to the
        # plugin's path directory
        return ['common_tasks.test_tasks.fib',
                'common_tasks.test_tasks.fail',
                'common_tasks.test_tasks.cancel',
                'common_tasks.test_tasks.girder_client']
