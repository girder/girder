from click_plugins import with_plugins
from pkg_resources import iter_entry_points
import click


@with_plugins(iter_entry_points('girder.cli_plugins'))
@click.group(help='Girder: data management platform for the web.',
             context_settings=dict(help_option_names=['-h', '--help']))
@click.version_option(message='%(version)s')
def main():
    pass
