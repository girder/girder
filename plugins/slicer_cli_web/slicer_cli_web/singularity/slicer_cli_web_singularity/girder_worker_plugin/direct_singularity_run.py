"""Celery task replacing ``direct_docker_run.run`` for apptainer execution."""

import logging
import os
from contextlib import contextmanager
from uuid import uuid4

from girder_worker.app import app
from girder_worker.singularity.girder_worker_singularity.tasks import (SingularityTask,
                                                                       singularity_run)
from slicer_cli_web.girder_worker_plugin import direct_docker_run
from slicer_cli_web.girder_worker_plugin.cli_progress import CLIProgressCLIWriter

from ..commands import SingularityCommands
from ..job import _is_nvidia_img, generate_image_name_for_singularity

logger = logging.getLogger(__name__)


@contextmanager
def _skip_docker_path_adjustment():
    """
    Suppress direct_docker_run's docker-socket based host path resolution while
    resolving direct file paths: there is no docker socket in singularity mode,
    and the worker's local filesystem paths are used as-is (they must be
    visible to the compute node via a shared filesystem).
    """
    original = direct_docker_run._adjust_docker_path
    direct_docker_run._adjust_docker_path = _identity_path
    try:
        yield
    finally:
        direct_docker_run._adjust_docker_path = original


def _identity_path(path):
    return path


class DirectSingularityTask(SingularityTask):
    def __call__(self, *args, **kwargs):
        with _skip_docker_path_adjustment():
            extra_volumes = direct_docker_run._resolve_direct_file_paths(
                args, kwargs)
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

    logs_dir = os.getenv('GIRDER_WORKER_SINGULARITY_LOGS_DIR')
    if logs_dir is None:
        raise Exception(
            'The GIRDER_WORKER_SINGULARITY_LOGS_DIR environment variable '
            'must be set to a writable directory path for singularity task logs'
        )
    kwargs['nvidia'] = _is_nvidia_img(image)

    # Change to reflect JOBID for logs later
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
