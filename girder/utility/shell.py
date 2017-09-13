#!/usr/bin/env python
# -*- coding: utf-8 -*-

###############################################################################
#  Copyright Kitware Inc.
#
#  Licensed under the Apache License, Version 2.0 ( the "License" );
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
###############################################################################

import click
import girder

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


@click.command(context_settings=dict(help_option_names=['-h', '--help']))
@click.option('--plugins', default=None, help='Comma separated list of plugins to import.')
def main(plugins):
    if plugins is not None:
        plugins = plugins.split(',')

    webroot, appconf = configureServer(plugins=plugins)

    _launchShell({
        'webroot': webroot,
        'appconf': appconf
    })


if __name__ == '__main__':
    main()
