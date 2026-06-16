import os
import subprocess
import sys
import threading
import time

from girder.models.setting import Setting

from girder_worker import logger
from girder_worker.docker import utils

from .girder_plugin import PluginSettings


def slurm_dispatch(task, container_args, run_kwargs, read_streams, write_streams, log_file_name,
                   progress_writer=None):
    apptainer_command, slurm_config = _slurm_apptainer_config(container_args, **run_kwargs)
    try:
        monitor_thread = _monitor_apptainer_job(
            apptainer_command, slurm_config, log_file_name, progress_writer=progress_writer)

        def check_job_cancellation():
            # Check if the cancel event is called and the job_id is set for the current
            # job thread we are intending to cancel.
            if task.canceled and monitor_thread.job_id:
                try:
                    returnCode = subprocess.call(['scancel', monitor_thread.job_id])
                    if returnCode != 0:
                        raise Exception(f'Failed to Cancel job with jobID {monitor_thread.job_id}')
                except Exception as e:
                    logger.info(f'Error Occured {e}')
            return not monitor_thread.is_alive()

        utils.select_loop(exit_condition=check_job_cancellation,
                          readers=read_streams,
                          writers=write_streams)
    finally:
        if progress_writer is not None:
            try:
                progress_writer.close()
            except Exception:
                logger.exception('Failed to close slurm progress writer')
        logger.info('DONE')
        # from girder_worker_singularity.tasks.utils import remove_tmp_folder_apptainer
        # TODO: removing the below line. remove_tmp_folder_apptainer's argument should be a list of paths
        # remove_tmp_folder_apptainer(container_args) # TODO: need to replace?
        # TODO: ^ is this even necessary?


def get_slurm_job_status(job_id):
    process = subprocess.run(['scontrol', 'show', 'job', job_id], capture_output=True)
    if process.returncode != 0:
        logger.error(f'Failed to get job status with error code {process.returncode}')
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


def _monitor_apptainer_job(apptainer_command, slurm_config, log_file_name, progress_writer=None):
    submit_script = os.getenv('GIRDER_WORKER_SLURM_SUBMIT_SCRIPT')
    # TODO: check for validity ^

    def submit_job_and_monitor_status():
        # TODO: cleanup log files
        submit_command = ['sbatch', f'--error={log_file_name}', f'--output={log_file_name}']
        submit_command.extend(slurm_config)
        submit_command.append(submit_script)
        submit_command.extend(apptainer_command)

        try:
            # Submit the job to the HPC
            print('running', submit_command)
            process = subprocess.run(submit_command, capture_output=True)
            if process.returncode != 0:
                raise Exception(f'Failed to submit job with error code {process.returncode}')

            sbatch_cli_stdout = process.stdout.decode('utf-8').strip()

            # Expecting output like 'Submitted batch job {job_id}'
            if 'Submitted batch job' not in sbatch_cli_stdout:
                raise Exception(f'Expected job_id, got: `{sbatch_cli_stdout}`')

            job_id = sbatch_cli_stdout.split(' ')[-1]
            logger.info(f'Job submitted with job id {job_id}')

            threading.current_thread().job_id = job_id # TODO: refactor this holdover from UF

            with open(log_file_name, 'r') as log_file:
                while True:
                    lines = log_file.readlines()
                    if lines:
                        _write_log_output(''.join(lines), progress_writer=progress_writer)

                    status = get_slurm_job_status(job_id)

                    if status in ['COMPLETED', 'FAILED', 'CANCELLED']:
                        logger.info(f'Job finished with status {status}')
                        # TODO: handle girder job status updates
                        if status == 'FAILED':
                            raise Exception(f'Slurm job {job_id} exited as {status}')
                        break

                    if status in ['BOOT_FAIL', 'DEADLINE', 'NODE_FAIL', 'OUT_OF_MEMORY', 'PREEMPTED', 'TIMEOUT']:
                        logger.error(f'Job failed with status {status}')
                        break

                    if status == 'INVALID':
                        logger.error(f'Job status is invalid: {status}, exiting.')
                        break

                    time.sleep(10)

        except Exception as e:
            print(f'Error Occured {e}')

    # Start the job monitor in a new thread
    monitor_thread = SlurmThread(target=submit_job_and_monitor_status, daemon=True)
    monitor_thread.start()

    return monitor_thread


def _slurm_apptainer_config(container_args=None, **kwargs):
    image = kwargs['image']
    container_args = container_args or kwargs['container_args'] or []
    try:
        slurm_config = _get_slurm_config(container_args, kwargs)
        container_args = _process_container_args(container_args, kwargs)

        logger.info('Running container: image: %s args: %s kwargs: %s'
                    % (image, container_args, kwargs))

        apptainer_command = _generate_apptainer_command(container_args, kwargs)

        return apptainer_command, slurm_config
    except Exception as e:
        logger.exception(e)
        raise Exception(e)


def _process_container_args(container_args, kwargs):
    volumes = kwargs['volumes'] or {}
    prefix = os.getenv('GIRDER_WORKER_SLURM_MOUNT_PREFIX')

    def find_matching_volume_key(path):
        for key, value in volumes.items():
            if path.startswith(value['bind']):
                # Append the suffix from the original path that isn't part of the 'bind' path
                suffix = path[len(value['bind']):] if value['bind'] != path else ''
                if 'assetstore' in key:
                    key = prefix + key
                # Replace spaces in suffix with underscores
                new_key = key + suffix.replace(' ', '_') # TODO: causing file name bug???
                return new_key
        return path  # Replace spaces in paths that don't match any volume
    try:
        # Replace paths in container_args with their corresponding volume keys
        container_args = [str(find_matching_volume_key(arg)) for arg in container_args]
    except Exception as e:
        logger.info(f'error {e}')

    # Remove all arguments that start with '--slurm_' & their values from container_args
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
    image = kwargs.pop('image', None)
    apptainer_command = []
    if not image:
        raise Exception(' Issue with Slicer_Cli_Plugin_Image. Plugin Not available') # TODO: remove

    sif_directory = os.getenv('SIF_IMAGE_PATH')
    image_full_path = os.path.join(sif_directory, image)

    try:
        pwd = kwargs['pwd']
        if not pwd:
            raise Exception('PWD cannot be empty')
        apptainer_command.extend(['--pwd', pwd])

        apptainer_command.append('--bind')
        volumes = ''
        for key, value in kwargs.get('volumes').items():
            # TODO: make this robust, currently only works for tmp volume mount
            # TODO: ^ when do things get mounted to docker like this?
            # volumes += f'{value["bind"]}:{key},'
            volumes += f'{key},'
        volumes = volumes[:-1] # remove trailing comma
        apptainer_command.append(volumes)

        apptainer_command.append(image_full_path)
        apptainer_command.append(kwargs.get('entrypoint', './docker-entrypoint.sh'))
        apptainer_command.extend(container_args)
    except Exception as e:
        logger.info(f'Error occured - {e}')
        raise Exception(f'Error Occured - {e}')
    return apptainer_command


def _get_slurm_config(container_args, kwargs):
    # # Use this function to add or modify any configuration parameters for the SLURM job
    # config_defaults = {
    #     # '--qos': Setting().get(PluginSettings.SLURM_QOS),
    #     # '--account': Setting().get(PluginSettings.SLURM_ACCOUNT),
    #     # '--mem': Setting().get(PluginSettings.SLURM_MEM),
    #     '--ntasks': Setting().get(PluginSettings.SLURM_NTASKS),
    #     # '--time': Setting().get(PluginSettings.SLURM_TIME),
    #     # '--partition': Setting().get(PluginSettings.SLURM_PARTITION),
    #     '--gres': Setting().get(PluginSettings.SLURM_GRES_CONFIG),
    #     # '--cpus-per-task': Setting().get(PluginSettings.SLURM_CPUS)
    # }

    # config = {k: kwargs.get(k, config_defaults[k]) for k in config_defaults}

    # slurm_config = [f'{k}={v}' for k, v in config.items() if v is not None]
    slurm_config = []
    for i, arg in enumerate(container_args):
        if arg.startswith('--slurm_'):
            # Extract the slurm config argument and its value
            arg_name = arg.lstrip('--slurm_')
            if i + 1 < len(container_args):
                arg_value = container_args[i + 1]
                slurm_config.append(f'--{arg_name}={arg_value}')
            else:
                logger.error(f'Missing value for {arg}, skipping.')

    logger.info(f'SLURM CONFIG = {slurm_config}')
    return slurm_config


class SlurmThread(threading.Thread):
    """
    This is a custom Thread class in order to handle cancelling a slurm job outside of the thread
    since the task context object is not available inside the thread.
    Methods:
    __init__(self,target, daemon) - Initialize the thread similar to threading. Thread class,
                                    requires a job_id param to keep track of the job_id
    run(self) - This method is used to run the target function. This is essentially called when
                you do thread.start()
    """

    def __init__(self, target, daemon=False):
        super().__init__(daemon=daemon)
        self.target = target
        self.job_id = None

    def run(self):
        if self.target:
            self.target()
