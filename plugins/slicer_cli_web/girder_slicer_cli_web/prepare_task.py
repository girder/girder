import json
import logging
import os

import jinja2
from girder.api.rest import RestException
from girder.constants import AccessType
from girder.exceptions import FilePathException
from girder.models.file import File
from girder.models.folder import Folder
from girder.models.setting import Setting
from girder.utility.model_importer import ModelImporter

from .cli_utils import (SLICER_TYPE_TO_GIRDER_MODEL_MAP, is_girder_api, is_on_girder,
                        return_parameter_file_name)

OPENAPI_DIRECT_TYPES = {'boolean', 'integer', 'float', 'double', 'string'}
FOLDER_SUFFIX = '_folder'

logger = logging.getLogger(__name__)


def _to_file_volume(param, model):
    from girder_worker.docker.transforms.girder import (GirderFileIdToVolume,
                                                        GirderFolderIdToVolume,
                                                        GirderItemIdToVolume)
    from girder_plugin_worker.constants import PluginSettings

    from .girder_worker_plugin.direct_docker_run import DirectGirderFileIdToVolume

    girder_type = SLICER_TYPE_TO_GIRDER_MODEL_MAP[param.typ]

    if girder_type == 'folder':
        return GirderFolderIdToVolume(model['_id'], folder_name=model['name'])
    elif girder_type == 'item':
        return GirderItemIdToVolume(model['_id'])

    if not Setting().get(PluginSettings.DIRECT_PATH):
        return GirderFileIdToVolume(model['_id'], filename=model['name'])

    try:
        path = File().getLocalFilePath(model)
        return DirectGirderFileIdToVolume(model['_id'], direct_file_path=path,
                                          filename=model['name'])
    except FilePathException:
        return GirderFileIdToVolume(model['_id'], filename=model['name'])


def _to_girder_api(param, value):
    from .girder_worker_plugin.direct_docker_run import GirderApiUrl, GirderToken

    if value:
        return value
    if param.name == 'girderApiUrl':
        return GirderApiUrl()
    elif param.name == 'girderToken':
        return GirderToken()
    return value


def _parseParamValue(param, value, user, token):
    if isinstance(value, bytes):
        value = value.decode('utf8')

    param_id = param.identifier()
    if is_on_girder(param):
        girder_type = SLICER_TYPE_TO_GIRDER_MODEL_MAP[param.typ]
        curModel = ModelImporter.model(girder_type)
        loaded = curModel.load(value, level=AccessType.READ, user=user)
        if not loaded:
            raise RestException('Invalid %s id (%s).' % (curModel.name, str(value)))
        return loaded

    try:
        if param.isVector():
            return '%s' % ', '.join(map(str, json.loads(value)))
        elif (param.typ in OPENAPI_DIRECT_TYPES
                or param.typ == 'string-enumeration'
                or param.typ in SLICER_TYPE_TO_GIRDER_MODEL_MAP):
            return str(value)
        else:  # json
            return str(json.loads(value))
    except json.JSONDecodeError:
        msg = 'Error: Parameter value is not in json.dumps format\n' \
              '  Parameter name = %r\n  Parameter type = %r\n' \
              '  Value passed = %r' % (param_id, param.typ, value)
        logger.exception(msg)
        raise RestException(msg)


def _processTemplates(value, param=None, templateParams=None):
    """
    Given a value that could be a string with jinja2-like template values, if
    template parameters are supplied, replace the templated parts of the string
    with the appropriate values.  Chained template references are not resolved
    (e.g., referring to {{parameter_other}} where the other parameter contains
    a template like {{now}} will probably result in the unprocessed template
    value).

    :param value: the object that might contain templates to be replaced.  If
        there are no templates, this is returned unchanged.
    :param param: a cli parameter, optional.  This extends the available
        template keys to include default, description, index, label, and name
        directly from the cli parameter.  'extension' is the first
        fileExtension, if it exists.  'reference' and 'reference_base' are
        mapped to the parameter listed in the cli parameter reference if it is
        populated in the templateParams as 'parameter_<reference>'.
    :param templateParams: a dictionary of template keys and values.  This
        typically contains task, title, image, now, YYYY, MM, DD, hh, mm, ss,
        parameter_<parameter name> and parameter_<parameter name>_base.
    :returns: either the original value if there were no templates, or a string
        with the templates replaced with their values.
    """
    if value == '__default__' and param:
        value = param.default
    if not templateParams:
        return value
    if param:
        templateParams = templateParams.copy()
        for key in {'default', 'description', 'index', 'label', 'name'}:
            if getattr(param, key, None) is not None:
                templateParams[key] = getattr(param, key)
        if getattr(param, 'fileExtensions', None) is not None and len(param.fileExtensions) >= 1:
            templateParams['extension'] = param.fileExtensions[0]
        reference = getattr(param, 'reference', None)
        key = f'parameter_{reference}'
        if key in templateParams:
            templateParams['reference'] = templateParams[key]
            templateParams['reference_base'] = templateParams[f'{key}_base']
    try:
        newvalue = jinja2.Template(str(value)).render(templateParams)
        if newvalue != str(value):
            logger.info('Replaced templated parameter %s with %s.', value, newvalue)
            return newvalue
    except Exception:
        logger.exception('Failed to repalce templated parameter %r', value)
    return value


def _add_optional_input_param(param, args, user, token, templateParams):
    if param.identifier() not in args:
        return []
    value = _parseParamValue(param, args[param.identifier()], user, token)

    container_args = []
    if param.longflag:
        container_args.append(param.longflag)
    elif param.flag:
        container_args.append(param.flag)
    else:
        return []

    if is_on_girder(param):
        # Bindings
        container_args.append(_to_file_volume(param, value))
    elif is_girder_api(param):
        # Bindings
        container_args.append(_to_girder_api(param, value))
    else:
        value = _processTemplates(value, param, templateParams)
        container_args.append(value)
    return container_args


def _add_optional_output_param(param, args, user, result_hooks, reference, templateParams):
    from girder_worker.docker.transforms import VolumePath
    from girder_worker.docker.transforms.girder import GirderUploadVolumePathToFolder

    if (not param.isExternalType() or not is_on_girder(param)
            or param.identifier() not in args or (param.identifier() + FOLDER_SUFFIX) not in args):
        return []
    value = args[param.identifier()]
    value = _processTemplates(value, param, templateParams)
    folder = args[param.identifier() + FOLDER_SUFFIX]

    container_args = []
    if param.longflag:
        container_args.append(param.longflag)
    elif param.flag:
        container_args.append(param.flag)
    else:
        return []

    instance = Folder().load(folder, level=AccessType.WRITE, user=user)
    if not instance:
        raise RestException('Invalid Folder id (%s).' % (str(folder)))

    # Output Binding !!
    path = VolumePath(value)
    container_args.append(path)
    ref = reference.copy()
    ref['identifier'] = param.identifier()
    result_hooks.append(GirderUploadVolumePathToFolder(
        path, folder, upload_kwargs={'reference': json.dumps(ref)}))

    return container_args


def _add_indexed_input_param(param, args, user, token, templateParams=None):
    value = _parseParamValue(param, args[param.identifier()], user, token)

    if is_on_girder(param):
        # Bindings
        return _to_file_volume(param, value), value['name']
    if is_girder_api(param):
        return _to_girder_api(param, value), value['name']
    value = _processTemplates(value, param, templateParams)
    return value, None


def _add_indexed_output_param(param, args, user, result_hooks, reference, templateParams):
    from girder_worker.docker.transforms import VolumePath
    from girder_worker.docker.transforms.girder import GirderUploadVolumePathToFolder

    value = args[param.identifier()]
    value = _processTemplates(value, param, templateParams)
    if param.typ == 'string':
        return value
    folder = args[param.identifier() + FOLDER_SUFFIX]

    instance = Folder().load(folder, level=AccessType.WRITE, user=user)
    if not instance:
        raise RestException('Invalid Folder id (%s).' % (str(folder)))

    # Output Binding
    path = VolumePath(value)
    ref = reference.copy()
    ref['identifier'] = param.identifier()
    result_hooks.append(GirderUploadVolumePathToFolder(
        path, folder, upload_kwargs={'reference': json.dumps(ref)}))
    return path


def _populateTemplateParams(params, user, token, index_params, opt_params, templateParams=None):
    """
    Collect values and keys for processing templates.

    :param params: a dictionary of arguments for the cli.
    :param user: the authenticating user.
    :param token: the authenticating token.
    :param index_params: a list of cli parameters.
    :param opt_params: a list of cli parameters.
    :param templateParams: a dictionary of keys and values to always include in
        the template values, such as 'now', 'task', and 'title'.
    :returns: the collected templateParams.  This will be the supplied template
        parameters plus 'parameter_<name>' and 'parameter_<name>_base' for the
        cli arguments.
    """
    templateParams = templateParams.copy() if templateParams else {}
    for param in index_params + opt_params:
        if param.identifier() in params:
            try:
                value = _parseParamValue(param, params[param.identifier()], user, token)
            except Exception:
                continue
            value = value.get('name') if isinstance(value, dict) else value
            if value:
                templateParams[f'parameter_{param.name}'] = value
                templateParams[f'parameter_{param.name}_base'] = str(value).rsplit('.', 1)[0]
    return templateParams


def _addEnvironmentToTemplateParams(templateParams=None):
    """
    Add the local environment to the template parameters.  Only environment
    variables that start with SLICER_CLI_WEB_ are added, as to do otherwise
    could expose private data.

    :param templateParams: a dictionary of keys and values to always include in
        the template values, such as 'now', 'task', and 'title'.
    :returns: the adjusted templateParams.
    """
    templateParams = templateParams.copy() if templateParams else {}
    for key in os.environ:
        parts = key.split('SLICER_CLI_WEB_', 1)
        if len(parts) == 2:
            templateParams[f'env_{parts[1]}'] = os.environ[key]
    return templateParams


def prepare_task(params, user, token, index_params, opt_params,
                 has_simple_return_file, reference, templateParams=None):
    import uuid

    from girder_worker.docker.transforms import VolumePath
    from girder_worker.docker.transforms.girder import GirderUploadVolumePathToFolder

    uuidVal = str(uuid.uuid4())
    ca = []
    result_hooks = []
    primary_input_name = None

    templateParams = _addEnvironmentToTemplateParams(templateParams)
    templateParams = _populateTemplateParams(
        params, user, token, index_params, opt_params, templateParams)

    # Get primary name and reference
    for param in index_params:
        if param.channel != 'output':
            arg, name = _add_indexed_input_param(param, params, user, token)
            if (name and not primary_input_name
                    and SLICER_TYPE_TO_GIRDER_MODEL_MAP[param.typ] != 'folder'):
                primary_input_name = name
                reference['userId'] = str(user['_id'])
                value = _parseParamValue(param, params[param.identifier()], user, token)
                itemId = value['_id']
                if SLICER_TYPE_TO_GIRDER_MODEL_MAP[param.typ] == 'file':
                    reference['fileId'] = str(value['_id'])
                    itemId = value['itemId']
                reference['itemId'] = str(itemId)
                reference['uuid'] = uuidVal

    # optional params
    for param in opt_params:
        if param.channel == 'output':
            ca.extend(_add_optional_output_param(
                param, params, user, result_hooks, reference, templateParams))
        else:
            ca.extend(_add_optional_input_param(param, params, user, token, templateParams))

    if has_simple_return_file:
        param_id = return_parameter_file_name + FOLDER_SUFFIX
        param_name_id = return_parameter_file_name
        if param_id in params and param_name_id in params:
            value = params[return_parameter_file_name]
            value = _processTemplates(value, templateParams=templateParams)
            folder = params[return_parameter_file_name + FOLDER_SUFFIX]

            instance = Folder().load(folder, level=AccessType.WRITE, user=user)
            if not instance:
                raise RestException('Invalid Folder id (%s).' % (str(folder)))

            ca.append('--returnparameterfile')

            # Output Binding
            path = VolumePath(value)
            ca.append(path)
            ref = reference.copy()
            ref['identifier'] = 'returnparameterfile'
            result_hooks.append(GirderUploadVolumePathToFolder(
                path, folder, upload_kwargs={'reference': json.dumps(ref)}))

    # indexed params
    for param in index_params:
        if param.channel == 'output':
            ca.append(_add_indexed_output_param(
                param, params, user, result_hooks, reference, templateParams))
        else:
            arg, name = _add_indexed_input_param(param, params, user, token, templateParams)
            ca.append(arg)
            if name and not primary_input_name:
                primary_input_name = name

    return ca, result_hooks, primary_input_name
