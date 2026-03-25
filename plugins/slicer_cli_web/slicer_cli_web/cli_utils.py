"""utils for CLI spec handling."""
import io

from .ctk_cli_adjustment import CLIModule

return_parameter_file_name = 'returnparameterfile'

SLICER_TYPE_TO_GIRDER_MODEL_MAP = {
    'image': 'file',
    'file': 'file',
    'item': 'item',
    'directory': 'folder'
}

SLICER_SUPPORTED_TYPES = set(['boolean', 'integer', 'float', 'double', 'string',
                              'integer-vector', 'float-vector', 'double-vector', 'string-vector',
                              'integer-enumeration', 'float-enumeration', 'double-enumeration',
                              'string-enumeration',
                              'region'] + list(SLICER_TYPE_TO_GIRDER_MODEL_MAP.keys()))


def generate_description(clim):
    """Create CLI description string."""
    str_description = ['Description: <br/><br/>' + clim.description]

    if clim.version:
        str_description.append('Version: ' + clim.version)

    if clim.license:
        str_description.append('License: ' + clim.license)

    if clim.contributor:
        str_description.append('Author(s): ' + clim.contributor)

    if clim.acknowledgements:
        str_description.append('Acknowledgements: ' + clim.acknowledgements)

    return '<br/><br/>'.join(str_description)


def as_model(cliXML):
    """Parses cli xml spec."""
    stream = io.BytesIO(cliXML if isinstance(cliXML, bytes) else cliXML.encode('utf8'))
    return CLIModule(stream=stream)


def get_cli_parameters(clim):

    # get parameters
    index_params, opt_params, simple_out_params = clim.classifyParameters()

    # perform sanity checks
    for param in index_params + opt_params:
        if param.typ not in SLICER_SUPPORTED_TYPES:
            raise Exception(
                'Parameter type %s is currently not supported' % param.typ
            )

    # sort indexed parameters in increasing order of index
    index_params.sort(key=lambda p: p.index)

    # sort opt parameters in increasing order of name for easy lookup
    def get_flag(p):
        if p.flag is not None:
            return p.flag.strip('-')
        elif p.longflag is not None:
            return p.longflag.strip('-')
        else:
            return None

    opt_params.sort(key=lambda p: get_flag(p))

    return index_params, opt_params, simple_out_params


def is_on_girder(param):
    if param.reference == '_girder_id_':
        return False
    return param.typ in SLICER_TYPE_TO_GIRDER_MODEL_MAP


def is_girder_api(param):
    return param.name in {'girderApiUrl', 'girderToken'}
