import json
import os
import subprocess

import logging

from slicer_cli_web.models import DockerImageError, DockerImageNotFoundError

from .commands import SingularityCommands, run_command
from .utils import (
    generate_image_name_for_singularity,
    sanitize_and_return_json,
    switch_to_sif_image_folder,
)

logger = logging.getLogger(__name__)


def is_valid_path(path):
    """
    Check if the provided path is a valid and accessible path in the file system.

    Parameters:
    path (str): The path to check.

    Returns:
    bool: True if the path is valid and accessible, False otherwise.
    """
    return os.path.exists(path) and os.access(path, os.R_OK)


def is_singularity_installed(path=None):
    """
    This function is used to check whether singularity is availble on the target system.
    This function is useful to make sure that singularity is accessible from a SLURM job submitted
    to HiperGator

    Args:
        path (str, optional): If the user wants to provide a specific path where singularity is
                              installed, you can provide that path. Defaults to None.

    Returns:
    bool: True if singualrity is successfully accessible on the target system. False otherwise
    """
    try:
        logger.info('Checking path')
        if path and is_valid_path(path):
            os.chdir(path)
    except Exception:
        logger.exception(f'{path} is not a valid path')
        raise Exception(
            f'{path} is not a valid path'
        )
    try:
        subprocess.run(SingularityCommands.singularity_version(), check=True)
        logger.info('Singularity env available')
    except Exception as e:
        logger.info(f'Exception {e} occured')
        raise e


def find_local_singularity_image(name: str, path=''):
    """
    Check if the image is present locally on the system in a specified path. For our usecase, we
    insall the images to a specific path on /blue directory, which can be modified via the argument
    to the function

    Args:
        name(str, required) - The name of the docker image with the tag <image>:<tag>.
        path(str, optional) - This path refers to the path on the local file system designated for
                              placing singularity images after they are pulled from the interweb.
    Returns:
    bool: True if singularity image is avaialble on the given path on host system. False otherwise.

    """
    try:
        sif_name = generate_image_name_for_singularity(name)
    except Exception:
        logger.exception("There's an error with the image name. Please check again and try")
        raise Exception("There's an error with the image name. Please check again and try")
    if not path:
        path = os.getenv('SIF_IMAGE_PATH', '')
        if not is_valid_path(path):
            logger.exception(
                'Please provide a valid path or set the environment variable "SIF_IMAGE_PATH" and'
                'ensure the path has appropriate access')
            raise Exception(
                'Please provide a valid path or set the environment variable "SIF_IMAGE_PATH" and'
                'ensure the path has appropriate access')
    return os.path.exists(os.path.join(path, sif_name))


def pull_image_and_convert_to_sif(names):
    """
    This is the function similar to the pullDockerImage function that pulls the image from
    Dockerhub or other instances if it's supported in the future
    Args:
    names(List(str), required) -> The list of image names of the format <img>:<tag>

    Raises:
    If pulling of any of the images fails, the function raises an error with the list of images
    that failed.
    """
    failedImageList = []
    for name in names:
        try:
            logger.info(f'Starting to pull image {name}')
            pull_cmd = SingularityCommands.singularity_pull(name)
            subprocess.run(pull_cmd, check=True)
        except Exception as e:
            logger.info(f'Failed to pull image {name}: {e}')
            failedImageList.append(name)
    if len(failedImageList) != 0:
        raise DockerImageNotFoundError('Could not find multiple images ',
                                       image_name=failedImageList)


def _is_nvidia_img(imageName):
    switch_to_sif_image_folder()
    inspect_labels_cmd = SingularityCommands.singularity_inspect(imageName)
    try:
        res = run_command(inspect_labels_cmd)
        res = sanitize_and_return_json(res)
        nvidia = res.get('com.nvidia.volumes.needed', None)
        if not nvidia:
            return False
        return True
    except Exception as e:
        raise Exception(f'Error occurred inspecting image for NVIDIA labels: {e}')


def get_local_singularity_output(imgName, cmdArg: str):
    """
    This function is used to run the singularity command locally for non-resource intensive tasks
    such as getting schema, environment variables and so on and return that output to the calling
    function
    """
    try:
        cwd = SingularityCommands.get_work_dir(imgName)
        if not cwd:
            logger.exception('Please set the entry_path env variable on the Docker Image')
            raise Exception('Please set the entry_path env variable on the Docker Image')
        run_parameters = f'--cwd {cwd}'
        cmd = SingularityCommands.singualrity_run(
            imgName, run_parameters=run_parameters, container_args=cmdArg)
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        return res.stdout
    except Exception as e:
        raise Exception(f'error occured {e}')


def find_and_remove_local_sif_files(name: str, path=None):
    try:
        sif_name = generate_image_name_for_singularity(name)
    except Exception:
        logger.exception("There's an error with the image name. Please check again and try")
        raise Exception("There's an error with the image name. Please check again and try")
    if not path:
        path = os.getenv('SIF_IMAGE_PATH', '')
        if not is_valid_path(path):
            logger.exception(
                'Please provide a valid path or set the environment variable "SIF_IMAGE_PATH" and'
                'ensure the path has appropriate access')
            raise Exception(
                'Please provide a valid path or set the environment variable "SIF_IMAGE_PATH" and'
                'ensure the path has appropriate access')
        filename = os.path.join(path, sif_name)
        if os.path.exists(filename):
            os.remove(filename)
