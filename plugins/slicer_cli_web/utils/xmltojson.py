# requires xmljson

import argparse
import json
import sys
from collections import OrderedDict

import xmljson
import yaml

try:
    from lxml.etree import parse
except ImportError:
    from xml.etree.ElementTree import parse


if __name__ == '__main__':  # noqa
    parser = argparse.ArgumentParser(prog='xmltojson')
    parser.add_argument('src', type=argparse.FileType(), nargs='?',
                        default=sys.stdin, help='Defaults to stdin.')
    parser.add_argument('-o', '--dest', type=argparse.FileType('w'),
                        default=sys.stdout, help='Defaults to stdout.')
    parser.add_argument('-y', '--yaml', action='store_true', default=False,
                        help='Output yaml.')
    args = parser.parse_args()

    data = xmljson.yahoo.data(parse(args.src).getroot())['executable']
    if not args.yaml:
        data['$schema'] = 'slicer_cli_web/models/schema.json'
        if hasattr(data, 'move_to_end'):
            data.move_to_end('$schema', last=False)
    for key, value in list(data.items()):
        if value == {} or value is None:
            data.pop(key)
    paramgroups = data.pop('parameters')
    if not isinstance(paramgroups, list):
        paramgroups = [paramgroups]
    data['parameter_groups'] = []
    for ingroup in paramgroups:
        copylabels = {'label', 'description', 'advanced'}
        group = {k: v for k, v in ingroup.items() if k in copylabels}
        for (k, kcast) in {
            'advanced': lambda x: str(x).lower() == 'true',
        }.items():
            if k in group:
                group[k] = kcast(group[k])
        group['parameters'] = []
        for key, params in ingroup.items():
            if key not in copylabels:
                if not isinstance(params, list):
                    params = [params]
                for param in params:
                    param['type'] = key
                    cast = {
                        'boolean': lambda x: str(x).lower() == 'true',
                        'integer': int,
                        'float': float,
                        'double': float}.get(key.split('-', 1)[0], str)
                    if hasattr(param, 'move_to_end'):
                        param.move_to_end('type', last=False)
                    if key.endswith('-vector') and param.get('default'):
                        param['default'] = [cast(v) for v in param['default'].split(',')]
                    elif param.get('default'):
                        param['default'] = cast(param['default'])
                    if param.get('constraints'):
                        for k, v in param['constraints'].items():
                            param['constraints'][k] = cast(v)
                    group['parameters'].append(param)
                    if key.endswith('-enumeration') and (
                            param.get('element') or param.get('enumeration')):
                        enumer = (param.pop('element') if param.get('element') else
                                  param.pop('enumeration').pop('element'))
                        if not isinstance(enumer, list):
                            enumer = list(enumer)
                        param['enumeration'] = [cast(v) for v in enumer]
                    for (k, kcast) in {
                        'index': int,
                        'multiple': lambda x: str(x).lower() == 'true',
                    }.items():
                        if k in param:
                            param[k] = kcast(param[k])
        data['parameter_groups'].append(group)
    if not args.yaml:
        result = json.dumps(data, indent=2)
    else:
        def represent_dict_order(self, data):
            return self.represent_mapping('tag:yaml.org,2002:map', data.items())

        yaml.add_representer(OrderedDict, represent_dict_order)
        result = yaml.dump(data)
    args.dest.write(result)
