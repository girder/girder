from girder_worker import GirderWorkerPluginABC
from girder_worker.singularity.girder_worker_singularity import singularity_enabled


class SlicerCLISingularityWebWorkerPlugin(GirderWorkerPluginABC):
    def __init__(self, app, *args, **kwargs):
        self.app = app

    def task_imports(self):
        if not singularity_enabled():
            return []
        return [
            'slicer_cli_web.singularity.slicer_cli_web_singularity.'
            'girder_worker_plugin.direct_singularity_run',
        ]
