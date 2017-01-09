import ctk_cli
import itertools
import os

from girder.models.model_base import ValidationException
from girder.plugins.worker import constants

_SLICER_TO_GIRDER_WORKER_TYPE_MAP = {
    'boolean': 'boolean',
    'integer': 'integer',
    'float': 'number',
    'double': 'number',
    'string': 'string',
    'integer-vector': 'integer_list',
    'float-vector': 'number_list',
    'double-vector': 'number_list',
    'string-vector': 'string_list',
    'integer-enumeration': 'integer',
    'float-enumeration': 'number',
    'double-enumeration': 'number',
    'string-enumeration': 'string',
    'file': 'file',
    'directory': 'folder',
    'image': 'file',
    'pointfile': 'file'
}

_SLICER_TYPE_TO_GIRDER_MODEL_MAP = {
    'image': 'file',
    'file': 'file',
    'directory': 'folder'
}


def parseSlicerCliXml(fd):
    """
    Parse a slicer CLI XML document into a form suitable for use
    in the worker.

    :param fd: A file descriptor representing the XML document to parse.
    :type fd: file-like
    :returns: A dict of information about the CLI.
    """
    cliSpec = ctk_cli.CLIModule(stream=fd)

    description = '\n\n'.join((
        '**Description**: %s' % cliSpec.description,
        '**Author(s)**: %s' % cliSpec.contributor,
        '**Version**: %s' % cliSpec.version,
        '**License**: %s' % cliSpec.license,
        '**Acknowledgements**: %s' % (cliSpec.acknowledgements or '*none*'),
        '*This description was auto-generated from the Slicer CLI XML specification.*'
    ))

    info = {
        'title': cliSpec.title,
        'description': description,
        'args': [],
        'inputs': [],
        'outputs': []
    }

    args, opts, outputs = cliSpec.classifyParameters()

    for param in itertools.chain(args, opts):
        if param.typ not in _SLICER_TO_GIRDER_WORKER_TYPE_MAP.keys():
            raise ValidationException('Parameter type %s is currently not supported' % param.typ)

    args.sort(key=lambda p: p.index)
    opts.sort(key=lambda p: p.flag or p.longflag)

    inputArgs = [a for a in args if a.channel == 'input']
    inputOpts = [o for o in opts if o.channel == 'input']
    outputArgs = [a for a in args if a.channel == 'output']
    outputOpts = [o for o in opts if o.channel == 'output']

    def ioSpec(name, param, addDefault=False):
        format = _SLICER_TO_GIRDER_WORKER_TYPE_MAP[param.typ]
        spec = {
            'id': name.strip('-'),
            'name': param.label,
            'description': param.description,
            'type': format,
            'format': format
        }

        if param.isExternalType():
            spec['target'] = 'filepath'

        if addDefault and param.default is not None:
            spec['default'] = param.default

        return spec

    for param in inputOpts:
        name = param.flag or param.longflag
        info['inputs'].append(ioSpec(name, param, True))
        info['args'] += [name, '$input{%s}' % name.strip('-')]

    for param in outputOpts:
        name = param.flag or param.longflag
        info['outputs'].append(ioSpec(name, param))
        info['args'] += [
            param.flag or param.longflag,
            os.path.join(constants.DOCKER_DATA_VOLUME, name.strip('-'))
        ]

    for param in inputArgs:
        info['inputs'].append(ioSpec(param.name, param, True))
        info['args'].append('$input{%s}' % param.name)

    for param in outputArgs:
        info['outputs'].append(ioSpec(param.name, param))
        info['args'].append(os.path.join(constants.DOCKER_DATA_VOLUME, param.name))

    return info
