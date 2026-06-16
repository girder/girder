import json
import os


def sanitize_and_return_json(res: str):
    """
    This function tries to parse the given str as json in couple different ways. If the output is
    still not json or a python dictionary, it raises an error.
    """
    try:
        res = json.loads(res)
        # This is the form in which we get data back if we use the --json label in
        # singularity inspect
        return res['data']['attributes']['labels']
    except json.decoder.JSONDecodeError:
        # If the json label was excluded, we can still parse the labels manually
        # and create a dictionary
        res_dict = {}
        for label in res.split('\n'):
            if ': ' not in label:
                continue
            key, value = label.split(': ', 1)
            res_dict[key] = value
        return res_dict
    except Exception as e:
        raise Exception(f'Error occured when parsing labels as json {e}')


def is_valid_image_name_format(image_str: str):
    """
    This function is used to validate whether the user supplied a valid string <img>:<tag> as an
    argument for functions like singularity pull

    Args:
    image_str(str, required) - The string that needs to be validated.

    Returns:
    bool - True if the image is in a valid format, False otherwise.
    """
    if not image_str:
        return False
    return True if len(image_str.split(':')) == 2 else False


def generate_image_name_for_singularity(image_str: str):
    """
    We need to generate the image name for storing the .sif files on the filesystem so that it is
    standardized, so it can be referenced in future calls.

    Args:
    image_str (str,required) - the image_name in the format <img>:<tag>

    Return:
    str - A string that is to be used for the .sif filename
    """
    if not is_valid_image_name_format(image_str):
        raise Exception(
            f'Not a valid image name. Please pass the image name in the format {image_str}')
    image_str = image_str.replace('/', '_').replace(':', '_')
    return f'{image_str}.sif'


def switch_to_sif_image_folder(image_path: str = ''):
    """
    This function is used to handle Issues that is occuring when Singularity switches directory
    when running a plugin and not having the context of where the SIF IMAGES are located for
    subsequent image pulls.
    This function ensures that Singularity always looks for the plugins in the proper location

    Args:
    image_path (str, optional) - This parameter is highly optional and is not recommended unless a
    specific use-case arises in the future

    Returns:
    None

    Raises:
    This function raises an Exception if the SIF_IMAGE_PATH env variable is not set.

    """
    try:
        if not image_path:
            image_path = os.getenv('SIF_IMAGE_PATH')
        os.chdir(image_path + '/')
    except Exception:
        raise Exception('Please set the SIF_IMAGE_PATH environment variable to locate SIF images')
