from click_plugins import with_plugins
import click
import importlib.metadata


@with_plugins(importlib.metadata.entry_points().get('girder.cli_plugins'))
@click.group(help='Girder: data management platform for the web.',
             context_settings=dict(help_option_names=['-h', '--help']))
@click.version_option(message='%(version)s')
def main():
    pass
