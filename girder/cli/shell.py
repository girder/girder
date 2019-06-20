# -*- coding: utf-8 -*-
import click
import girder
import six
import sys

from girder.utility.server import configureServer


def _launchShell(context):
    """
    Launches a Python shell with the given context.

    :param context: A dictionary containing key value pairs
    of variable name -> value to be set in the newly
    launched shell.
    """
    header = 'Girder %s' % girder.__version__
    header += '\nThe current context provides the variables webroot and appconf for use.'

    try:
        from IPython import embed
        return embed(header=header, user_ns=context)
    except ImportError:
        import code
        return code.interact(banner=header, local=context)


@click.command('shell', short_help='Run a Girder shell.', help='Run an interactive Girder shell '
               'or a script in the Girder environment.')
@click.option('--plugins', default=None, help='Comma separated list of plugins to import.')
@click.argument('script', type=click.Path(exists=True, dir_okay=False), required=False)
@click.argument('args', nargs=-1, required=False)
def main(plugins, script, args):
    if plugins is not None:
        plugins = plugins.split(',')

    webroot, appconf = configureServer(plugins=plugins)

    if script is None:
        _launchShell({
            'webroot': webroot,
            'appconf': appconf
        })
    else:
        globals_ = {k: v for k, v in six.viewitems(globals()) if k not in {'__file__', '__name__'}}
        sys.argv = [script] + list(args)
        six.exec_(open(script, 'rb').read(), dict(
            webroot=webroot, appconf=appconf, __name__='__main__',
            __file__=script, **globals_))
