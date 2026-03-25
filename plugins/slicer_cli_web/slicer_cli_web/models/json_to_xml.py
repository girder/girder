import io
from xml.etree.ElementTree import Element, ElementTree, SubElement


def _copy(parent, data, *keys, **kwargs):
    for key in keys:
        if key in data:
            SubElement(parent, key).text = str(data[key])

    for key, value in kwargs.items():
        if key in data:
            SubElement(parent, value).text = str(data[key])


def _copy_attr(parent, data, *keys, **kwargs):
    for key in keys:
        if key in data:
            parent.set(key, str(data[key]))

    for key, value in kwargs.items():
        if key in data:
            parent.set(value, str(data[key]))


def _convert_param(parent, param):
    p = SubElement(parent, param['type'])
    if param.get('multiple'):
        p.set('multiple', 'true')

    _copy(p, param, 'label', 'description', 'name', 'index', 'channel')

    _copy_attr(p, param,
               'coordinateSystem', 'fileExtensions', 'defaultPathMatch',
               'defaultNameMatch', 'defaultRelativePath', 'shapes',
               image_type='type', table_type='type', geometry_type='type',
               transform_type='type')

    for key in ['flag', 'longflag']:
        if key not in param:
            continue
        val = param[key]
        flag = SubElement(p, key)
        if isinstance(val, dict):
            _copy_attr(flag, val, 'alias', 'deprecatedalias')
            flag.text = val['value']
        else:
            flag.text = val

    if 'default' in param:
        default_value = param['default']
        d = SubElement(p, 'default')
        if param['type'].endswith('-vector'):
            d.text = ','.join(str(v) for v in default_value)
        else:
            d.text = str(default_value)

    if 'enumeration' in param:
        for value in param['enumeration']:
            SubElement(p, 'element').text = str(value)

    if 'constraints' in param:
        c = SubElement(p, 'constraints')
        _copy(c, param['constraints'], 'minimum', 'maximum', 'step')

    if 'reference' in param:
        ref = param['reference']
        if isinstance(ref, dict):
            ref_e = SubElement(p, 'reference')
            _copy_attr(ref_e, ref, 'role', 'parameter')
            ref_e.text = ref['value']
        else:
            p.set('reference', ref)


def _convert_group(parent, group):
    parameters = SubElement(parent, 'parameters')
    if group.get('advanced'):
        parameters.set('advanced', 'true')
    _copy(parameters, group, 'label', 'description')

    if 'parameters' not in group:
        return

    for param in group['parameters']:
        _convert_param(parameters, param)


def json_to_xml(data):
    root = Element('executable')
    _copy(root, data, 'category', 'title', 'description', 'version', 'license',
          'contributor', 'acknowledgements',
          documentation_url='documentation-url')

    if 'parameter_groups' in data:
        for group in data['parameter_groups']:
            _convert_group(root, group)

    strio = io.StringIO()
    ElementTree(root).write(strio, 'unicode', True)
    return strio.getvalue()
