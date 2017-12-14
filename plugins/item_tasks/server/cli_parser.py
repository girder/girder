import ctk_cli
import itertools

from girder.exceptions import ValidationException

_SLICER_TO_GIRDER_WORKER_INPUT_TYPE_MAP = {
    'boolean': 'boolean',
    'integer': 'integer',
    'float': 'number',
    'double': 'number',
    'string': 'string',
    'integer-vector': 'integer-vector',
    'float-vector': 'number-vector',
    'double-vector': 'number-vector',
    'string-vector': 'string-vector',
    'integer-enumeration': 'number-enumeration',
    'float-enumeration': 'number-enumeration',
    'double-enumeration': 'number-enumeration',
    'string-enumeration': 'string-enumeration',
    'file': 'file',
    'directory': 'folder',
    'image': 'image',
    'pointfile': 'file',
    'region': 'region'
}

_SLICER_TO_GIRDER_WORKER_OUTPUT_TYPE_MAP = {
    'file': 'new-file',
    'image': 'new-file',
    'pointfile': 'new-file'
}

_SLICER_TYPE_TO_GIRDER_MODEL_MAP = {
    'image': 'image',
    'file': 'file',
    'directory': 'folder'
}


def _validateParam(param):
    if param.channel == 'input' and param.typ not in _SLICER_TO_GIRDER_WORKER_INPUT_TYPE_MAP:
        raise ValidationException(
            'Input parameter type %s is currently not supported.' % param.typ)

    if param.channel == 'output' and param.typ not in _SLICER_TO_GIRDER_WORKER_OUTPUT_TYPE_MAP:
        raise ValidationException(
            'Output parameter type %s is currently not supported.' % param.typ)


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
        _validateParam(param)

    args.sort(key=lambda p: p.index)
    opts.sort(key=lambda p: p.flag or p.longflag)

    inputArgs = [a for a in args if a.channel == 'input' or a.channel is None]
    inputOpts = [o for o in opts if o.channel == 'input' or o.channel is None]
    outputArgs = [a for a in args if a.channel == 'output']
    outputOpts = [o for o in opts if o.channel == 'output']

    def ioSpec(name, param, addDefault=False):
        if param.channel == 'output':
            typ = _SLICER_TO_GIRDER_WORKER_OUTPUT_TYPE_MAP[param.typ]
        else:
            typ = _SLICER_TO_GIRDER_WORKER_INPUT_TYPE_MAP[param.typ]

        spec = {
            'id': name,
            'name': param.label,
            'description': param.description,
            'type': typ,
            'format': typ
        }
        if param.reference:
            spec['extra'] = {'reference': param.reference}

        if typ in ('string-enumeration', 'number-enumeration'):
            spec['values'] = list(param.elements)

        if param.isExternalType():
            spec['target'] = 'filepath'

        if addDefault and param.default is not None:
            spec['default'] = {
                'data': param.default
            }

        return spec

    for param in inputOpts:
        name = param.flag or param.longflag
        info['inputs'].append(ioSpec(name, param, True))

        if param.typ == 'boolean':
            info['args'].append('$flag{%s}' % name)
        else:
            info['args'].append('%s=$input{%s}' % (name, name))

    for param in outputOpts:
        name = param.flag or param.longflag
        info['outputs'].append(ioSpec(name, param))
        info['args'].append('%s=$output{%s}' % (name, name))

    for param in inputArgs:
        info['inputs'].append(ioSpec(param.name, param, True))
        info['args'].append('$input{%s}' % param.name)

    for param in outputArgs:
        info['outputs'].append(ioSpec(param.name, param))
        info['args'].append('$output{%s}' % param.name)

    return info
