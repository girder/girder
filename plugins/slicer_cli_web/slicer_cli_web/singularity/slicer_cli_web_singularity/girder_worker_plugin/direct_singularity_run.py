import os
from uuid import uuid4

import logging
from girder_worker.app import app
from girder_worker.singularity.girder_worker_singularity.tasks import SingularityTask, singularity_run

from slicer_cli_web.girder_worker_plugin.cli_progress import CLIProgressCLIWriter
from slicer_cli_web.girder_worker_plugin.direct_docker_run import _resolve_direct_file_paths

from ..commands import SingularityCommands
from ..job import _is_nvidia_img, generate_image_name_for_singularity

logger = logging.getLogger(__name__)


class DirectSingularityTask(SingularityTask):
    def __call__(self, *args, **kwargs):
        extra_volumes = _resolve_direct_file_paths(args, kwargs)
        if extra_volumes:
            volumes = kwargs.setdefault('volumes', [])
            if isinstance(volumes, list):
                # list mode use
                volumes.extend(extra_volumes)
            else:
                for extra_volume in extra_volumes:
                    volumes.update(extra_volume._repr_json_())
        super().__call__(*args, **kwargs)


@app.task(base=DirectSingularityTask, bind=True)
def run(task, **kwargs):
    """Wraps singularity_run to support running singularity containers"""
    image = kwargs['image']
    kwargs['image'] = generate_image_name_for_singularity(image)

    pwd = SingularityCommands.get_work_dir(image)
    kwargs['pwd'] = pwd

    logs_dir = os.getenv('LOGS')
    if logs_dir is None:
        raise Exception(
            'The LOGS environment variable must be set to a writable directory path for singularity task logs')
    kwargs['nvidia'] = _is_nvidia_img(image)

    # Cahnge to reflect JOBID for logs later
    random_file_name = str(uuid4()) + 'logs.log'
    log_file_name = os.path.join(logs_dir, random_file_name)
    kwargs['log_file'] = log_file_name

    # Create file since it doesn't exist
    if not os.path.exists(log_file_name):
        with open(log_file_name, 'x'):
            pass

    if hasattr(task, 'job_manager'):
        kwargs['progress_writer'] = CLIProgressCLIWriter(task.job_manager)
    return singularity_run(task, **kwargs)
