from girder_worker import GirderWorkerPluginABC


class BaseTestPlugin(GirderWorkerPluginABC):
    def __init__(self, *args, **kwargs):
        pass

    def task_imports(self):
        return []


class TestPlugin1(BaseTestPlugin):
    pass


class TestPlugin2(BaseTestPlugin):
    def task_imports(self):
        return ['girder_worker._test_plugins.tasks']


class TestPluginException1(BaseTestPlugin):
    def __init__(self, *arg, **kwargs):
        raise Exception('Exception in constructor')


class TestPluginException2(BaseTestPlugin):
    def task_imports(self):
        raise Exception('Exception in task_imports')


class TestPluginInvalidModule(BaseTestPlugin):
    def task_imports(self):
        return ['not a valid module']
