import argparse
import girder_worker
import os
import sys


def get_config(section, option):
    return girder_worker.config.get(section, option)


def set_config(section, option, value):
    if not girder_worker.config.has_section(section):
        girder_worker.config.add_section(section)
    girder_worker.config.set(section, option, value)
    write_config()


def write_config(fd=None):
    if fd is None:
        path = os.path.join(girder_worker.PACKAGE_DIR, 'worker.local.cfg')
        with open(path, 'w') as fd:
            girder_worker.config.write(fd)
    else:
        girder_worker.config.write(fd)


def rm_config(section, option):
    girder_worker.config.remove_option(section, option)
    write_config()


def main():
    parser = argparse.ArgumentParser(
        description='Get and set configuration values for the worker')
    subparsers = parser.add_subparsers(help='sub-command help', dest='cmd')

    get_parser = subparsers.add_parser('get', help='get a config value')
    set_parser = subparsers.add_parser('set', help='set a config value')
    rm_parser = subparsers.add_parser('rm', help='remove a config option')
    subparsers.add_parser('list', help='show all config values')

    get_parser.add_argument(
        'section', help='The section containing the option.')
    get_parser.add_argument('option', help='The option to retrieve.')

    set_parser.add_argument(
        'section', help='The section containing the option.')
    set_parser.add_argument('option', help='The option to set.')
    set_parser.add_argument('value', help='The value to set the option to.')

    rm_parser.add_argument(
        'section', help='The section containing the option to remove.')
    rm_parser.add_argument('option', help='The option to remove.')

    args = parser.parse_args()

    if args.cmd == 'get':
        print(get_config(args.section, args.option))
    elif args.cmd == 'set':
        set_config(args.section, args.option, args.value)
    elif args.cmd == 'list':
        write_config(sys.stdout)
    elif args.cmd == 'rm':
        rm_config(args.section, args.option)


if __name__ == '__main__':
    main()  # pragma: no cover
