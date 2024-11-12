import json
import os
import subprocess
import sys


def processCLI(filename):
    try:
        with open(os.path.join(os.path.dirname(os.path.realpath(__file__)),
                               filename)) as f:
            list_spec = json.load(f)
    except Exception:
        print('Failed to parse %s' % filename)
        return
    if len(sys.argv) >= 2 and sys.argv[1] == '--list_cli':
        print(json.dumps(list_spec, sort_keys=True, indent=2, separators=(',', ': ')))
        return
    if len(sys.argv) < 2 or sys.argv[1][:1] == '-':
        print('%s --list_cli to get a list of available interfaces.' % __file__)
        print('%s <cli> --help for more details.' % __file__)
        return

    cli = os.path.normpath(sys.argv[1])

    cli = list_spec[cli].get('alias', cli)

    if list_spec[cli]['type'] == 'python':
        script_file = os.path.join(cli, os.path.basename(cli) + '.py')
        # python <cli-rel-path>/<cli-name>.py [<args>]
        subprocess.call([sys.executable, script_file] + sys.argv[2:])
    elif list_spec[cli]['type'] == 'cxx':
        script_file = os.path.join('.', cli, os.path.basename(cli))
        # ./<cli-rel-path>/<cli-name> [<args>]
        subprocess.call([script_file] + sys.argv[2:])
    else:
        raise Exception('CLIs of type %s are not supported' % list_spec[cli]['type'])


if __name__ == '__main__':
    processCLI('cli_list.json')
