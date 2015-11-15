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
"""
This module contains functions to install optional components
into the current Girder installation.  Note that Girder must
be restarted for these changes to take effect.
"""

import os
import girder
import pip
import subprocess
import tempfile

from girder import constants
from girder.utility.plugin_utilities import getPluginDir
from six.moves import urllib

version = constants.VERSION['apiVersion']
pluginDir = getPluginDir()
webRoot = os.path.join(constants.STATIC_ROOT_DIR, 'clients', 'web')


def print_version(parser):
    print(version)


def print_plugin_path(parser):
    print(pluginDir)


def print_web_root(parser):
    print(webRoot)


def fix_path(path):
    """
    Get an absolute path (while expanding ~).

    :param path: a filesystem path
    :type path: str
    :returns: an absolute path
    :rtype: str
    """
    return os.path.abspath(os.path.expanduser(path))


def install_web(parser):
    """
    Build and install Girder's web client. This runs `npm install` to execute
    the entire build and install process.
    """
    args = ('npm', 'install', '--production', '--unsafe-perm')
    proc = subprocess.Popen(args, cwd=girder.__path__[0])
    proc.communicate()

    if proc.returncode:
        raise Exception('Web client install failed: npm install returned %s.' %
                        proc.returncode)


def install_plugin(parser):
    """
    Install one or more plugins from the given source.  If no
    source is given, it will install all plugins in the release
    package on Github.  The source provided must be a directory
    or tarball containing one or more directories which
    will be installed as individual plugins.

    :param str src: source specification (filesystem or url)
    :param bool force: allow overwriting existing files
    :returns: a list of plugins that were installed
    :rtype: list
    """
    if source is None:  # pragma: no cover
        source = defaultSource + 'girder-plugins-' + version + '.tar.gz'

    found = []
    tmp = tempfile.mkdtemp()
    try:
        handle_source(source, tmp)

        plugins = []
        for pth in os.listdir(tmp):
            pth = os.path.join(tmp, pth)
            if os.path.isdir(pth):
                plugins.append(pth)

        for plugin in plugins:
            pluginName = os.path.split(plugin)[1]
            pluginTarget = os.path.join(pluginDir, pluginName)

            if os.path.exists(pluginTarget):
                if force:
                    shutil.rmtree(pluginTarget)
                else:
                    print(constants.TerminalColor.warning(
                        'A plugin already exists at %s, '
                        'use "force" to overwrite.' % pluginTarget
                    ))
                    continue
            found.append(pluginName)
            shutil.copytree(plugin, pluginTarget)
            requirements = os.path.join(pluginTarget, 'requirements.txt')
            if os.path.exists(requirements):  # pragma: no cover
                print(constants.TerminalColor.info(
                    'Attempting to install requirements for %s.\n' % pluginName
                ))
                if pip.main(['install', '-U', '-r', requirements]) != 0:
                    print(constants.TerminalColor.error(
                        'Failed to install requirements for %s.' % pluginName
                    ))
    finally:
        shutil.rmtree(tmp)
    return found

__all__ = ('install_plugin', 'install_web')


def main():
    """
    This is an entry point exposed in the python sdist package under the name
    "girder-install".
    """
    import argparse
    import sys

    parser = argparse.ArgumentParser(
        description='Install optional Girder components.  To get help for a subcommand, '
                    'try "%s <command> -h"' % sys.argv[0],
        epilog='This script supports installing from a url, a tarball, '
               'or a local path.  When installing with no sources specified, it will install '
               'from the main Girder repository corresponding to the Girder release '
               'currently installed.'
    )

    sub = parser.add_subparsers()

    plugin = sub.add_parser('plugin', help='Install a plugin.')
    plugin.set_defaults(func=install_plugin)

    web = sub.add_parser('web', help='Install web client libraries.')
    web.set_defaults(func=install_web)

    sub.add_parser(
        'version', help='Print the version of Girder.'
    ).set_defaults(func=print_version)

    sub.add_parser(
        'plugin-path', help='Print the currently configured plugin path.'
    ).set_defaults(func=print_plugin_path)

    sub.add_parser(
        'web-root', help='Print the current web root for static files.'
    ).set_defaults(func=print_web_root)

    parsed = parser.parse_args()
    parsed.func(parsed)
    # npm install --production --unsafe-perm
