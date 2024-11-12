import os
import pprint
import sys

from slicer_cli_web import CLIArgumentParser


def main(args):
    print('>> parsed arguments')
    pprint.pprint(vars(args))


if __name__ == '__main__':
    if len(sys.argv) == 2:
        if sys.argv[1] == '--json':
            json_spec_file = os.path.splitext(sys.argv[0])[0] + '.json'
            with open(json_spec_file) as f:
                print(f.read())
            sys.exit(0)
        if sys.argv[1] == '--yaml':
            yaml_spec_file = os.path.splitext(sys.argv[0])[0] + '.yaml'
            with open(yaml_spec_file) as f:
                print(f.read())
            sys.exit(0)

    main(CLIArgumentParser().parse_args())
