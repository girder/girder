import argparse
import os
import sys
from girder_client import _safeMakedirs
from six.moves.configparser import ConfigParser


class GirderConfig(object):

    def __init__(self, config_file=None, allow_no_value=True):
        _config_defaults = {
            'host': 'localhost',
            'scheme':  'http',
            'apiRoot': '/api/v1',
            'apiUrl': None,
            'port': None,
            'apiKey': None,
            'username': None,
            'password': None,
        }
        self.config = ConfigParser(_config_defaults, allow_no_value=allow_no_value)

        try:
            config_home = os.path.join(os.path.expanduser('~'), '.config')
        except ImportError:
            config_home = None

        if config_file is None:
            self.config_dir = os.environ.get('XDG_CONFIG_HOME', config_home)
            self.config_file = os.path.join(self.config_dir, "girder-cli.conf")
            self.config.read([os.path.join(self.config_dir, "girder-cli.conf")])
        else:
            self.config_file = config_file
            self.config_dir = os.path.dirname(self.config_file)

        if not os.path.isfile(self.config_file):
            print('The config file: "%s" does not exist. '
                  'Falling back to defaults.' % self.config_file)
        self.config.read([self.config_file])

        if not self.config.has_section("girder_client"):
            self.config.add_section("girder_client")

    def get_config(self, section, option):
        return self.config.get(section, option)

    def set_config(self, section, option, value):
        if not self.config.has_section(section):
            self.config.add_section(section)
        self.config.set(section, option, value)
        self.write_config()

    def write_config(self, fd=None):
        _safeMakedirs(self.config_dir)
        if fd is None:
            with open(self.config_file, 'w') as fd:
                self.config.write(fd)
        else:
            self.config.write(fd)

    def rm_config(self, section, option):
        self.config.remove_option(section, option)
        self.write_config()


def main():
    parser = argparse.ArgumentParser(
        description='Get and set configuration values for the client')
    parser.add_argument(
        '-c', required=False, default=None, dest='config',
        help='The location of the config file.')
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

    config = GirderConfig(args.config)

    if args.cmd == 'get':
        print(config.get_config(args.section, args.option))
    elif args.cmd == 'set':
        config.set_config(args.section, args.option, args.value)
    elif args.cmd == 'list':
        config.write_config(sys.stdout)
    elif args.cmd == 'rm':
        config.rm_config(args.section, args.option)

if __name__ == '__main__':
    main()  # pragma: no cover
