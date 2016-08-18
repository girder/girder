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

import sys
import os
import pip
import shutil
import subprocess

from girder import constants
from girder.utility.plugin_utilities import getPluginDir

version = constants.VERSION['apiVersion']
webRoot = os.path.join(constants.STATIC_ROOT_DIR, 'clients', 'web')

# monkey patch shutil for python < 3
if sys.version_info[0] == 2:
    import shutilwhich  # noqa


def print_version(parser):
    print(version)


def print_plugin_path(parser):
    print(getPluginDir())


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


def runNpmInstall(wd=None, dev=False, npm='npm'):
    """
    Use this to run `npm install` inside the package.
    """
    if shutil.which(npm) is None:
        print(constants.TerminalColor.error(
            'No npm executable was detected.  Please ensure the npm '
            'executable is in your path, or use the "--npm" option to '
            'provide a custom path.'
        ))
        raise Exception('npm executable not found')

    wd = wd or constants.PACKAGE_DIR

    args = (npm, 'install', '--production', '--unsafe-perm') if not dev \
        else (npm, 'install', '--unsafe-perm')

    proc = subprocess.Popen(args, cwd=wd)
    proc.communicate()

    if proc.returncode != 0:
        raise Exception('Web client install failed: npm install returned %s.' %
                        proc.returncode)


def install_web(opts=None):
    """
    Build and install Girder's web client. This runs `npm install` to execute
    the entire build and install process.
    """
    if opts is None:
        runNpmInstall()
    else:
        runNpmInstall(dev=opts.development, npm=opts.npm)


def install_plugin(opts):
    """
    Install a list of plugins into a packaged Girder environment. This first
    copies the plugin dir recursively into the Girder primary plugin directory,
    then installs all of its pip requirements from its requirements.txt file if
    one exists. After all plugins have finished installing, we run
    `npm install` to build all of the web client code.

    :param opts: Options controlling the behavior of this function. Must be an
        object with a "plugin" attribute containing a list of plugin paths, and
        a boolean "force" attribute representing the force overwrite flag.
    """
    for plugin in opts.plugin:
        pluginPath = fix_path(plugin)
        name = os.path.basename(pluginPath)

        print(constants.TerminalColor.info('Installing %s...' % name))

        if not os.path.isdir(pluginPath):
            raise Exception('Invalid plugin directory: %s' % pluginPath)

        if not opts.skip_requirements:
            requirements = [os.path.join(pluginPath, 'requirements.txt')]
            if opts.development:
                requirements.append(os.path.join(pluginPath, 'requirements-dev.txt'))
            for reqs in requirements:
                if os.path.isfile(reqs):
                    print(constants.TerminalColor.info(
                        'Installing pip requirements for %s from %s.' % (name, reqs)))

                    if pip.main(['install', '-r', reqs]) != 0:
                        raise Exception('Failed to install pip requirements at %s.' % reqs)

        targetPath = os.path.join(getPluginDir(), name)

        if (os.path.isdir(targetPath) and
                os.path.samefile(pluginPath, targetPath) and not
                opts.symlink ^ os.path.islink(targetPath)):
            # If source and dest are the same, we are done for this plugin.
            # Note: ^ is a logical xor - not xor means only continue if
            # symlink and islink() are either both false, or both true
            continue

        if os.path.exists(targetPath):
            if opts.force:
                print(constants.TerminalColor.warning(
                    'Removing existing plugin at %s.' % targetPath))

                if os.path.islink(targetPath):
                    os.unlink(targetPath)
                else:
                    shutil.rmtree(targetPath)

            else:
                raise Exception(
                    'Plugin already exists at %s, use "-f" to overwrite the existing directory.' %
                    targetPath)
        if opts.symlink:
            os.symlink(pluginPath, targetPath)
        else:
            shutil.copytree(pluginPath, targetPath)

    if not opts.skip_web_client:
        runNpmInstall(dev=opts.development, npm=opts.npm)


def main():
    """
    This is an entry point exposed in the python sdist package under the name
    "girder-install".
    """
    import argparse
    import sys

    parser = argparse.ArgumentParser(
        description='Install optional Girder components. To get help for a '
                    'subcommand, use "%s <command> -h"' % sys.argv[0])

    sub = parser.add_subparsers()

    plugin = sub.add_parser('plugin', help='Install plugins.')
    plugin.set_defaults(func=install_plugin)
    plugin.add_argument('-f', '--force', action='store_true',
                        help='Overwrite plugins if they already exist.')

    plugin.add_argument('-s', '--symlink', action='store_true',
                        help='Install by symlinking to the plugin directory.')

    plugin.add_argument('--skip-web-client', action='store_true',
                        help='Skip the step of running the web client build.')

    plugin.add_argument('--skip-requirements', action='store_true',
                        help='Skip the step of pip installing the requirements.txt file.')

    plugin.add_argument('--dev', action='store_true',
                        dest='development',
                        help='Install server/client development dependencies')

    plugin.add_argument('--npm', default="npm",
                        help='specify the full path to the npm executable.')

    plugin.add_argument('plugin', nargs='+',
                        help='Paths of plugins to install.')

    web = sub.add_parser('web', help='Build and install web client code.')

    web.add_argument('--dev', action='store_true',
                     dest='development',
                     help='Install client development dependencies')

    web.add_argument('--npm', default="npm",
                     help='specify the full path to the npm executable.')

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

if __name__ == '__main__':
    main()  # pragma: no cover
