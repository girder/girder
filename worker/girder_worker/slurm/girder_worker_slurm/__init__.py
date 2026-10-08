"""Slurm job submission for apptainer tasks executed by girder-worker.

When ``GIRDER_WORKER_SLURM_SUBMIT_SCRIPT`` is set on the worker, apptainer
tasks are submitted to a slurm cluster via ``sbatch`` and monitored with
``scontrol``. See the repository documentation for the full list of
environment variables.
"""

import os
import subprocess
import sys
import threading
import time

from girder_worker import logger
from girder_worker.docker import utils

# Poll interval (seconds) for `scontrol show job` while a submitted job runs.
SLURM_POLL_INTERVAL = 10

# Terminal slurm job states that indicate the job did not complete
# successfully.
SLURM_FAILURE_STATES = [
    'BOOT_FAIL',
    'CANCELLED',
    'DEADLINE',
    'FAILED',
    'NODE_FAIL',
    'OUT_OF_MEMORY',
    'PREEMPTED',
    'SPECIAL_EXIT',
    'TIMEOUT',
]


def slurm_dispatch(
    task,
    container_args,
    run_kwargs,
    read_streams,
    write_streams,
    log_file_name,
    progress_writer=None,
):
    apptainer_command, slurm_config = _slurm_apptainer_config(
        container_args,
        **run_kwargs,
    )
    monitor_thread = _monitor_apptainer_job(
        apptainer_command,
        slurm_config,
        log_file_name,
        progress_writer=progress_writer,
    )

    def check_job_cancellation():
        # Check if cancel was requested and this thread has a job id.
        if task.canceled and monitor_thread.job_id:
            try:
                return_code = subprocess.call(
                    ['scancel', monitor_thread.job_id]
                )
                if return_code != 0:
                    raise Exception(
                        'Failed to Cancel job with jobID '
                        f'{monitor_thread.job_id}'
                    )
            except Exception as e:
                logger.info(f'Error Occurred {e}')
        return not monitor_thread.is_alive()

    try:
        utils.select_loop(
            exit_condition=check_job_cancellation,
            readers=read_streams,
            writers=write_streams,
        )
    finally:
        if progress_writer is not None:
            try:
                progress_writer.close()
            except Exception:
                logger.exception('Failed to close slurm progress writer')
        logger.info('DONE')

    # Errors that occurred inside the monitor thread (submission failures,
    # failed slurm jobs, etc.) must fail the girder job, not just be logged.
    if monitor_thread.error is not None:
        raise monitor_thread.error
    if task.canceled:
        raise Exception('Slurm apptainer task was canceled')


def get_slurm_job_status(job_id):
    process = subprocess.run(
        ['scontrol', 'show', 'job', job_id],
        capture_output=True,
    )
    if process.returncode != 0:
        logger.error(
            'Failed to get job status with error code %s',
            process.returncode,
        )
        return 'INVALID'

    result = process.stdout.decode('utf-8')
    if 'JobState' not in result:
        logger.error(f'Expected JobState, got: `{result}`')
        return 'INVALID'

    scontrol_values = result.split()
    for value in scontrol_values:
        if 'JobState' in value:
            return value.split('=')[-1]

    return 'INVALID'


def _write_log_output(text, progress_writer=None):
    data = text.encode('utf-8', errors='replace')
    if progress_writer is not None:
        progress_writer.write(data)
    stdout = getattr(sys.stdout, 'buffer', sys.stdout)
    stdout.write(data)
    stdout.flush()


def _monitor_apptainer_job(
    apptainer_command,
    slurm_config,
    log_file_name,
    progress_writer=None,
):
    submit_script = os.getenv('GIRDER_WORKER_SLURM_SUBMIT_SCRIPT')
    if not submit_script:
        raise Exception(
            'GIRDER_WORKER_SLURM_SUBMIT_SCRIPT must be set to the path of a '
            'slurm submit script for slurm apptainer tasks'
        )
    if not os.path.isfile(submit_script):
        raise Exception(
            f'GIRDER_WORKER_SLURM_SUBMIT_SCRIPT ({submit_script}) does not '
            'reference an existing file'
        )

    def submit_job_and_monitor_status():
        submit_command = [
            'sbatch',
            f'--error={log_file_name}',
            f'--output={log_file_name}',
        ]
        submit_command.extend(slurm_config)
        submit_command.append(submit_script)
        submit_command.extend(apptainer_command)

        try:
            logger.info('Submitting slurm job: %s', submit_command)
            process = subprocess.run(submit_command, capture_output=True)
            if process.returncode != 0:
                stderr = process.stderr.decode('utf-8', errors='replace')
                raise Exception(
                    'Failed to submit job with error code '
                    f'{process.returncode}: {stderr.strip()}'
                )

            sbatch_cli_stdout = process.stdout.decode('utf-8').strip()

            # Expecting output like 'Submitted batch job {job_id}'
            if 'Submitted batch job' not in sbatch_cli_stdout:
                raise Exception(f'Expected job_id, got: `{sbatch_cli_stdout}`')

            job_id = sbatch_cli_stdout.split(' ')[-1]
            logger.info(f'Job submitted with job id {job_id}')

            threading.current_thread().job_id = job_id

            with open(log_file_name) as log_file:
                while True:
                    lines = log_file.readlines()
                    if lines:
                        _write_log_output(''.join(lines), progress_writer=progress_writer)

                    status = get_slurm_job_status(job_id)

                    if status == 'COMPLETED':
                        logger.info(f'Job finished with status {status}')
                        break

                    if status in SLURM_FAILURE_STATES or status == 'INVALID':
                        raise Exception(f'Slurm job {job_id} exited as {status}')

                    time.sleep(SLURM_POLL_INTERVAL)

        except Exception as e:
            logger.exception('Slurm apptainer job failed')
            threading.current_thread().error = e

    # Start the job monitor in a new thread
    monitor_thread = SlurmThread(
        target=submit_job_and_monitor_status,
        daemon=True,
    )
    monitor_thread.start()

    return monitor_thread


def _slurm_apptainer_config(container_args=None, **kwargs):
    image = kwargs['image']
    container_args = container_args or kwargs.get('container_args') or []
    slurm_config = _get_slurm_config(container_args)
    container_args = _process_container_args(container_args, kwargs)

    logger.info('Running container: image: %s args: %s kwargs: %s'
                % (image, container_args, kwargs))

    apptainer_command = _generate_apptainer_command(container_args, kwargs)

    return apptainer_command, slurm_config


def _process_container_args(container_args, kwargs):
    volumes = kwargs.get('volumes') or {}
    # The mount prefix maps assetstore-like volume keys onto the compute
    # node's filesystem; it may be empty or unset.
    prefix = os.getenv('GIRDER_WORKER_SLURM_MOUNT_PREFIX') or ''

    def find_matching_volume_key(path):
        for key, value in volumes.items():
            bind = (value or {}).get('bind')
            if not bind or not path.startswith(bind):
                continue
            # Append the suffix from the original path that isn't part
            # of the bind path.
            suffix = path[len(bind):] if bind != path else ''
            if 'assetstore' in key:
                key = prefix + key
            # Replace spaces in suffix with underscores
            return key + suffix.replace(' ', '_')
        # Paths that don't match any volume are passed through unchanged
        return path

    container_args = [
        str(find_matching_volume_key(arg))
        for arg in container_args
    ]

    # Remove all --slurm_ arguments and the value that follows each one.
    filtered_args = []
    it = iter(container_args)
    for arg in it:
        if arg.startswith('--slurm_'):
            next(it, None)
        else:
            filtered_args.append(arg)

    return filtered_args


def _generate_apptainer_command(container_args, kwargs):
    container_args = container_args or []
    image = kwargs.get('image')
    if not image:
        raise Exception(
            ' Issue with Slicer_Cli_Plugin_Image. Plugin Not available'
        )

    sif_directory = os.getenv('SIF_IMAGE_PATH')
    image_full_path = os.path.join(sif_directory, image) if sif_directory else image

    pwd = kwargs.get('pwd')
    if not pwd:
        raise Exception('PWD cannot be empty')
    apptainer_command = ['--pwd', pwd]

    apptainer_command.append('--bind')
    volumes = ''
    for key, _value in (kwargs.get('volumes') or {}).items():
        # TODO: make this robust, currently only works for tmp volume mount
        # TODO: ^ when do things get mounted to docker like this?
        volumes += f'{key},'
    volumes = volumes[:-1]  # remove trailing comma
    apptainer_command.append(volumes)

    apptainer_command.append(image_full_path)
    apptainer_command.append(
        kwargs.get('entrypoint', './docker-entrypoint.sh')
    )
    apptainer_command.extend(container_args)
    return apptainer_command


def _get_slurm_config(container_args):
    slurm_config = []
    has_partition = False
    for i, arg in enumerate(container_args):
        if arg.startswith('--slurm_'):
            # Extract the slurm config argument and its value
            arg_name = arg.removeprefix('--slurm_')
            has_partition = has_partition or arg_name == 'partition'
            if i + 1 < len(container_args):
                arg_value = container_args[i + 1]
                slurm_config.append(f'--{arg_name}={arg_value}')
            else:
                logger.error(f'Missing value for {arg}, skipping.')

    # The submit script ships a default partition directive; command line
    # options passed to sbatch take precedence over #SBATCH directives, so
    # the partition can be overridden with this environment variable.
    partition = os.getenv('GIRDER_WORKER_SLURM_PARTITION')
    if partition and not has_partition:
        slurm_config.append(f'--partition={partition}')

    logger.info(f'SLURM CONFIG = {slurm_config}')
    return slurm_config


class SlurmThread(threading.Thread):
    """
    Thread wrapper used to support external SLURM job cancellation.

    The task context object is not available inside the thread.

    Methods:
        __init__(self, target, daemon): initialize the thread and store
            a job id.
        run(self): execute the target function when ``start()`` is called.
    """

    def __init__(self, target, daemon=False):
        super().__init__(daemon=daemon)
        self.target = target
        self.job_id = None
        self.error = None

    def run(self):
        if self.target:
            self.target()
