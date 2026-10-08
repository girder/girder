"""Singularity task execution for girder-worker.

This module ports the apptainer (singularity) execution path from the
``girder_worker`` ``slurm`` branch to the girder 5 worker API. Tasks are only
registered when the ``GIRDER_WORKER_SINGULARITY_ENABLED`` environment variable
is set, so an installation without the flag behaves exactly like stock
girder-worker.
"""

import os
import shutil
import subprocess
import sys

from girder_worker import logger
from girder_worker.docker import utils
from girder_worker.docker.io import FDReadStreamConnector, FDWriteStreamConnector, StdStreamWriter
from girder_worker.docker.tasks import DockerTask, _handle_streaming_args

BLACKLISTED_DOCKER_RUN_ARGS = ['tty', 'detach']


class SingularityTask(DockerTask):
    # Called by DockerTask after __call__ completion
    def _cleanup_temp_volumes(self, temp_volumes, default_temp_volume):
        # This override skips the docker-based chmod_writable() step of
        # DockerTask._cleanup_temp_volumes: there is no docker daemon in
        # singularity mode. Files written by apptainer containers (or slurm
        # jobs running apptainer) are owned by the invoking user, so they can
        # be removed directly.
        try:
            temp_volumes = [
                v.host_path for v in temp_volumes if os.path.exists(v.host_path)
            ]
            if default_temp_volume._transformed:
                temp_volumes.append(default_temp_volume.host_path)

            for v in temp_volumes:
                shutil.rmtree(v)
        except Exception:
            logger.exception('Failed to clean up temporary singularity volumes')


class _FileWriter:
    def __init__(self, fileobj):
        self._fileobj = fileobj

    def write(self, buf):
        written = self._fileobj.write(buf)
        self._fileobj.flush()
        return written

    def close(self):
        self._fileobj.close()


class _FileObjectReader:
    def __init__(self, fileobj):
        self._fileobj = fileobj

    def read(self, n):
        return self._fileobj.read(n)

    def fileno(self):
        return self._fileobj.fileno()

    def close(self):
        self._fileobj.close()


class _CompositeWriter:
    def __init__(self, *writers):
        self._writers = [writer for writer in writers if writer is not None]

    def write(self, buf):
        written = 0
        for writer in self._writers:
            result = writer.write(buf)
            if result is not None:
                written = max(written, result)
        return written

    def close(self):
        for writer in self._writers:
            try:
                writer.close()
            except Exception:
                logger.exception('Failed to close singularity stream writer')


def _resolve_image_path(image):
    if os.path.isabs(image):
        return image
    sif_directory = os.getenv('SIF_IMAGE_PATH')
    if sif_directory:
        return os.path.join(sif_directory, image)
    return image


def _bind_specs(volumes):
    specs = []
    seen = set()
    for host_path, value in (volumes or {}).items():
        mode = (value or {}).get('mode', 'rw')
        bind = (value or {}).get('bind')
        container_paths = [host_path] if not bind or bind == host_path else [host_path, bind]
        for container_path in container_paths:
            spec = f'{host_path}:{container_path}:{mode}'
            if spec not in seen:
                specs.append(spec)
                seen.add(spec)
    return specs


def _apptainer_exec_command(image, container_args=None, **kwargs):
    container_args = container_args or []
    cmd = ['apptainer', 'exec']
    if kwargs.get('nvidia'):
        cmd.append('--nv')

    pwd = kwargs.get('pwd')
    if pwd:
        cmd.extend(['--pwd', pwd])

    bind_specs = _bind_specs(kwargs.get('volumes'))
    if bind_specs:
        cmd.extend(['--bind', ','.join(bind_specs)])

    cmd.append(_resolve_image_path(image))

    entrypoint = kwargs.get('entrypoint')
    if entrypoint is not None:
        if isinstance(entrypoint, (list, tuple)):
            cmd.extend(entrypoint)
        else:
            cmd.append(entrypoint)

    cmd.extend(container_args)
    return cmd


def slurm_configured():
    """
    Return True when slurm job submission is configured via the
    ``GIRDER_WORKER_SLURM_SUBMIT_SCRIPT`` environment variable. When unset,
    apptainer tasks are executed directly on the worker host.
    """
    return bool(os.getenv('GIRDER_WORKER_SLURM_SUBMIT_SCRIPT'))


def singularity_run(task, **kwargs):  # noqa: C901
    volumes = kwargs.pop('volumes', {})
    container_args = kwargs.pop('container_args', [])
    stream_connectors = kwargs.get('stream_connectors') or []
    progress_writer = kwargs.pop('progress_writer', None)
    image = kwargs.pop('image', None)
    entrypoint = './docker-entrypoint.sh'
    # TODO: use `apptainer sif dump 3 <image> | jq -r .Entrypoint`.

    if not image:
        logger.exception('Image name cannot be empty')
        raise Exception('Image name cannot be empty')

    run_kwargs = {
        'tty': False,
        'volumes': volumes,
        'entrypoint': entrypoint,
        'image': image,
    }

    # Allow run args to be overridden,filter out any we don't want to override
    extra_run_kwargs = {k: v for k, v in kwargs.items() if k not in BLACKLISTED_DOCKER_RUN_ARGS}
    run_kwargs.update(extra_run_kwargs)

    log_file_name = kwargs.get('log_file')
    if log_file_name is None:
        raise Exception('singularity_run requires a "log_file" keyword argument')

    container_args, read_streams, write_streams = _handle_streaming_args(container_args)
    for connector in stream_connectors:
        if isinstance(connector, FDReadStreamConnector):
            read_streams.append(connector)
        elif isinstance(connector, FDWriteStreamConnector):
            write_streams.append(connector)
        else:
            raise TypeError(
                "Expected 'FDReadStreamConnector' or 'FDWriterStreamConnector', received '%s'"
                % type(connector))

    for stream in read_streams:
        stream.open()

    if slurm_configured():
        from girder_worker.slurm.girder_worker_slurm import slurm_dispatch

        slurm_dispatch(
            task,
            container_args,
            run_kwargs,
            read_streams,
            write_streams,
            log_file_name,
            progress_writer=progress_writer,
        )
        results = []
        if hasattr(task.request, 'girder_result_hooks'):
            results = (None,) * len(task.request.girder_result_hooks)
        return results

    local_run_kwargs = run_kwargs.copy()
    local_run_kwargs.pop('image', None)
    cmd = _apptainer_exec_command(image, container_args, **local_run_kwargs)
    logger.info('Running Apptainer command: %s', cmd)

    log_writer = None
    if log_file_name:
        log_writer = _FileWriter(open(log_file_name, 'ab'))

    stdout_stream = getattr(sys.stdout, 'buffer', sys.stdout)
    stdout_writer = _CompositeWriter(
        log_writer,
        progress_writer,
        StdStreamWriter(stdout_stream) if progress_writer is None else None,
    )

    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )

    read_streams.append(FDReadStreamConnector(
        input=_FileObjectReader(process.stdout),
        output=stdout_writer,
    ))

    try:
        def exit_condition():
            return process.poll() is not None or task.canceled

        utils.select_loop(exit_condition=exit_condition,
                          readers=read_streams,
                          writers=write_streams)
    finally:
        if task.canceled and process.poll() is None:
            process.terminate()
        if log_writer is not None:
            try:
                log_writer.close()
            except Exception:
                logger.exception('Failed to close singularity log writer')

    return_code = process.wait()
    if task.canceled:
        raise Exception('Apptainer task was canceled')
    if return_code != 0:
        raise Exception(f'Apptainer command failed with exit code {return_code}')

    results = []
    if hasattr(task.request, 'girder_result_hooks'):
        results = (None,) * len(task.request.girder_result_hooks)

    return results
