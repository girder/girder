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
import re
import select
import shutil
import six
import subprocess
import string
import sys

from girder import constants
from girder import plugin

version = constants.VERSION['apiVersion']
webRoot = os.path.join(constants.STATIC_ROOT_DIR, 'clients', 'web')

# monkey patch shutil for python < 3
if not six.PY3:
    import shutilwhich  # noqa


def _pipMain(*args):
    """Run `pip *args` in a system independent way.

    This replaces the old method of calling `pip.main` directly which
    was broken by pip 9.0.2.
    """
    pipCommand = (sys.executable, '-m', 'pip') + args
    subprocess.check_call(pipCommand)


def print_version(parser):
    print(version)


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


def _pipeOutputToProgress(proc, progress):
    """
    Pipe the latest contents of the stdout and stderr pipes of a subprocess into the
    message of a progress context.

    :param proc: The subprocess to listen to.
    :type proc: subprocess.Popen
    :param progress: The progress context.
    :type progress: girder.utility.progress.ProgressContext
    """
    fds = [proc.stdout, proc.stderr]
    while True:
        ready = select.select(fds, (), fds, 1)[0]

        for pipe in (proc.stdout, proc.stderr):
            if pipe in ready:
                buf = os.read(pipe.fileno(), 1024)
                if buf:
                    buf = buf.decode('utf8', errors='ignore')
                    # Remove ANSI escape sequences
                    buf = re.sub('(\x9B|\x1B\[)[0-?]*[ -\/]*[@-~]', '', buf)
                    # Filter out non-printable characters
                    msg = ''.join(c for c in buf if c in string.printable)
                    if msg:
                        progress.update(message=msg)
                else:
                    pipe.close()
                    fds.remove(pipe)
        if (not fds or not ready) and proc.poll() is not None:
            break
        elif not fds and proc.poll() is None:
            proc.wait()


def runWebBuild(wd=None, dev=False, npm='npm', progress=None):
    """
    Use this to run `npm install` inside the package. Also builds the web code
    using `npm run build`.

    :param wd: Working directory to use. If not specified, uses the girder package directory.
    :param dev: Whether to build the code in dev mode.
    :type dev: bool
    :param npm: Path to the npm executable to use.
    :type npm: str
    :param allPlugins: Enable this to build all available plugins as opposed to only enabled ones.
    :type allPlugins: bool
    :param plugins: A specific set of plugins to build.
    :type plugins: str, list or None
    :param progress: A progress context for reporting output of the tasks.
    :type progress: ``girder.utility.progress.ProgressContext`` or None
    :param noPlugins: Enable this to build the girder web with no additional plugins.
    :type noPlugins: bool
    """
    if shutil.which(npm) is None:
        print(constants.TerminalColor.error(
            'No npm executable was detected.  Please ensure the npm '
            'executable is in your path, or use the "--npm" option to '
            'provide a custom path.'
        ))
        raise Exception('npm executable not found')

    npmInstall = [npm, 'install', '--unsafe-perm', '--no-save']
    if not dev:
        npmInstall.append('--production')

    wd = wd or constants.PACKAGE_DIR
    env = 'dev' if dev else 'prod'
    quiet = '--no-progress=false' if sys.stdout.isatty() else '--no-progress=true'
    commands = [
        npmInstall,
        [npm, 'run', 'build', '--',
         quiet, '--env=%s' % env] + ['--plugins=%s' % ','.join(plugin.allPlugins())]
    ]

    for cmd in commands:
        if progress and progress.on:
            proc = subprocess.Popen(cmd, cwd=wd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            _pipeOutputToProgress(proc, progress)
        else:
            proc = subprocess.Popen(cmd, cwd=wd)
            proc.communicate()

        if proc.returncode != 0:
            raise Exception('Web client install failed: `%s` returned %s.' %
                            (' '.join(cmd), proc.returncode))


def _runWatchCmd(*args):
    try:
        subprocess.Popen(args, cwd=constants.PACKAGE_DIR).wait()
    except KeyboardInterrupt:
        pass


def install_web(opts=None):
    """
    Build and install Girder's web client, or perform a watch on the web
    client or a specified plugin. For documentation of all the options, see
    the argparse configuration for the "web" subcommand in the main() function.
    """
    if opts is None:
        runWebBuild()
    elif opts.watch:
        _runWatchCmd('npm', 'run', 'watch')
    else:
        runWebBuild(dev=opts.development, npm=opts.npm)


def _install_plugin_reqs(pluginPath, name, dev=False):
    setupPath = os.path.join(pluginPath, 'setup.py')
    requirementsPath = os.path.join(pluginPath, 'requirements.txt')
    devRequirementsPath = os.path.join(pluginPath, 'requirements-dev.txt')

    # Install plugin dependencies
    if os.path.isfile(setupPath):
        print(constants.TerminalColor.info('Installing %s as a package.' % name))
        _pipMain('install', '-e', pluginPath)
    elif os.path.isfile(requirementsPath):
        print(constants.TerminalColor.info('Installing requirements.txt for %s.' % name))
        _pipMain('install', '-r', requirementsPath)

    # Install plugin development dependencies
    if dev and os.path.isfile(devRequirementsPath):
        print(constants.TerminalColor.info(
            'Installing requirements-dev.txt for %s.' % name))
        _pipMain('install', '-r', devRequirementsPath)


def install_plugin(opts):
    """
    Install a list of plugins into a packaged Girder environment. This first copies the plugin dir
    recursively into the Girder primary plugin directory, then installs the plugin using pip (if
    setup.py exists) or installs dependencies from a requirements.txt file (otherwise, and if that
    file exists). After all plugins have finished installing, we run `npm install` to build all of
    the web client code.

    :param opts: Options controlling the behavior of this function. Must be an
        object with a "plugin" attribute containing a list of plugin paths, and
        a boolean "force" attribute representing the force overwrite flag.
    """
    pass


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

    plugin.add_argument('--skip-requirements', action='store_true',
                        help='Skip the step of pip installing the plugin dependencies.')

    plugin.add_argument('--dev', action='store_true',
                        dest='development',
                        help='Install development dependencies.')

    plugin.add_argument('--npm', default='npm',
                        help='Override the full path to the npm executable.')

    plugin.add_argument('plugin', nargs='+',
                        help='Paths of plugins to install.')

    web = sub.add_parser('web', help='Build and install web client code.')

    web.add_argument('--dev', action='store_true',
                     dest='development',
                     help='Build Girder in development mode.')

    web.add_argument('--npm', default='npm',
                     help='Override the full path to the npm executable.')

    web.add_argument('--watch', action='store_true',
                     help='Watch Girder\'s core, automatically rebuilding in development mode when '
                          'it changes.')

    web.add_argument('--watch-plugin', default='',
                     help='Watch a plugin, automatically rebuilding in development mode when it '
                          'changes.')

    web.add_argument('--plugin-prefix', default='plugin',
                     help='When watching a plugin, watch this output bundle name. Defaults to '
                          '"plugin".')

    web.set_defaults(func=install_web)

    sub.add_parser(
        'version', help='Print the version of Girder.'
    ).set_defaults(func=print_version)

    sub.add_parser(
        'web-root', help='Print the current web root for static files.'
    ).set_defaults(func=print_web_root)

    parsed = parser.parse_args()

    if hasattr(parsed, 'func'):
        parsed.func(parsed)
    else:
        parser.print_help()
