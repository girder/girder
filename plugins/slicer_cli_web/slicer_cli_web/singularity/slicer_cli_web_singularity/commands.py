import json
import logging
import os
import shlex
import subprocess

from .utils import generate_image_name_for_singularity

logger = logging.getLogger(__name__)


class SingularityCommands:
    @staticmethod
    def singularity_version():
        """
        This method is used to check whether apptainer is currently installed on the system.
        """
        return ['apptainer', '--version']

    @staticmethod
    def _sif_image_path(image_name: str):
        """Return absolute SIF path when SIF_IMAGE_PATH is configured."""
        sif_name = generate_image_name_for_singularity(image_name)
        base_path = os.getenv('SIF_IMAGE_PATH')
        if base_path:
            return os.path.join(base_path, sif_name)
        return sif_name

    @staticmethod
    def singularity_pull(name: str, uri: str = 'docker'):
        """
        This method is used to generate the command for the singualrity pull function for pulling
        images from online.
        Args:
        name(str.required) - image name and tag as a single string '<image_name>:<tag>'
        uri(str, optional) - image uri (necessary for Dockerhub)

        Returns:
        List of strings for singularity subprocess command.
        """
        sif_path = SingularityCommands._sif_image_path(name)
        return ['apptainer', 'pull', '--force', sif_path, f'{uri}://{name}']

    @staticmethod
    def _json_descriptor_ids(sif_path: str):
        """Return JSON descriptor ids from `apptainer sif list` output."""
        list_output = run_command(['apptainer', 'sif', 'list', sif_path])
        descriptor_ids = []
        for line in list_output.splitlines():
            if 'JSON.Generic' not in line:
                continue
            parts = [part.strip() for part in line.split('|')]
            if not parts:
                continue
            descriptor_id = parts[0].split()[0]
            if descriptor_id.isdigit():
                descriptor_ids.append(descriptor_id)
        return descriptor_ids

    @staticmethod
    def get_work_dir(imageName: str):
        sif_path = SingularityCommands._sif_image_path(imageName)

        descriptor_ids = SingularityCommands._json_descriptor_ids(sif_path)
        errors = []
        for descriptor_id in descriptor_ids:
            try:
                descriptor_json = run_command(['apptainer', 'sif', 'dump', descriptor_id, sif_path])
                descriptor_data = json.loads(descriptor_json)
                if isinstance(descriptor_data, dict):
                    work_dir = descriptor_data.get('WorkingDir')
                    if work_dir:
                        return work_dir
            except Exception as exc:
                errors.append(f'{descriptor_id}: {exc}')

        logger.warning(
            'Could not determine WorkingDir for %s from JSON descriptors %s; defaulting to "/". Errors: %s',
            sif_path,
            descriptor_ids,
            '; '.join(errors) if errors else 'none',
        )
        return '/'

    @staticmethod
    def singualrity_run(imageName: str, run_parameters=None, container_args=None):
        sif_path = SingularityCommands._sif_image_path(imageName)
        cmd = ['apptainer', 'run', '--no-mount', '/cmsuf']
        if run_parameters:
            cmd.extend(shlex.split(run_parameters))
        cmd.append(sif_path)
        if container_args:
            cmd.extend(shlex.split(container_args))
        return cmd

    @staticmethod
    def singularity_get_env(image: str, run_parameters=None):
        sif_path = SingularityCommands._sif_image_path(image)
        cmd = ['apptainer', 'exec', '--cleanenv']
        if run_parameters:
            cmd.extend(shlex.split(run_parameters))
        cmd.append(sif_path)
        cmd.append('env')
        return cmd

    @staticmethod
    def singularity_inspect(imageName, option='-l', json_format=True):
        """
        This function is used to get the apptainer command for inspecting the sif file. By default,
        it inspects the labels in a json format, but you can you any option allowed by apptainer
        by setting the option flag appropriately and also the json flag is set to True by default.
        """
        sif_path = SingularityCommands._sif_image_path(imageName)
        cmd = ['apptainer', 'inspect']
        if json_format:
            cmd.append('--json')
        cmd.append(option)
        cmd.append(sif_path)
        return cmd


def run_command(cmd):
    try:
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        output = res.stdout.decode('utf-8') if isinstance(res.stdout, bytes) else res.stdout
        return output.strip()
    except subprocess.CalledProcessError as exc:
        stderr = exc.stderr.decode('utf-8', errors='ignore').strip() if exc.stderr else ''
        logger.exception('Error occurred when running command %s', cmd)
        raise Exception(f'Error running command {cmd}: {stderr or exc}') from exc
    except Exception as exc:
        logger.exception('Error occurred when running command %s', cmd)
        raise Exception(f'Error running command {cmd}: {exc}') from exc
