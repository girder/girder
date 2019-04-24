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

import json
import os
from pkg_resources import resource_filename
from subprocess import check_call
import shutil
import sys

import click
import six

from girder.constants import SettingKey, STATIC_ROOT_DIR
from girder.models.setting import Setting
from girder.plugin import allPlugins, getPlugin

# monkey patch shutil for python < 3
if not six.PY3:
    import shutilwhich  # noqa

_GIRDER_BUILD_ASSETS_PATH = os.path.realpath(resource_filename('girder', 'web_client'))


@click.command(name='build', help='Build web client static assets.')
@click.option('--dev/--no-dev', default=False,
              help='Build girder client for development.')
@click.option('--watch', default=False, is_flag=True,
              help='Build girder library bundle in watch mode (implies --dev --no-reinstall).')
@click.option('--watch-plugin',
              help='Build a girder plugin bundle in watch mode (implies --dev --no-reinstall).')
@click.option('--npm', default=os.getenv('NPM_EXE', 'npm'),
              help='Full path to the npm executable to use.')
@click.option('--reinstall/--no-reinstall', default=True,
              help='Force regenerate node_modules.')
@click.option('--static-public-path', help='URL public path of static content.')
def main(dev, watch, watch_plugin, npm, reinstall, static_public_path):
    if shutil.which(npm) is None:
        raise click.UsageError(
            'No npm executable was detected.  Please ensure the npm executable is in your '
            'path, use the --npm flag, or set the "NPM_EXE" environment variable.'
        )

    if watch and watch_plugin:
        raise click.UsageError('--watch and --watch-plugins cannot be used together')
    if watch or watch_plugin:
        dev = True
        reinstall = False

    staging = _GIRDER_BUILD_ASSETS_PATH
    _generatePackageJSON(staging, os.path.join(_GIRDER_BUILD_ASSETS_PATH, 'package.json.template'))

    if not os.path.isdir(os.path.join(staging, 'node_modules')) or reinstall:
        # The autogeneration of package.json breaks how package-lock.json is
        # intended to work.  If we don't delete it first, you will frequently
        # get "file doesn't exist" errors.
        npmLockFile = os.path.join(staging, 'package-lock.json')
        if os.path.exists(npmLockFile):
            os.unlink(npmLockFile)
        installCommand = [npm, 'install']
        if not dev:
            installCommand.append('--production')
        check_call(installCommand, cwd=staging)

    quiet = '--no-progress=false' if sys.stdout.isatty() else '--no-progress=true'
    buildCommand = [
        npm, 'run', 'build', '--',
        '--static-path=%s' % STATIC_ROOT_DIR,
        '--static-public-path=%s' % (
            static_public_path or Setting().get(SettingKey.STATIC_PUBLIC_PATH)),
        quiet
    ]
    if watch:
        buildCommand.append('--watch')
    if watch_plugin:
        buildCommand.extend([
            '--watch',
            'webpack:plugin_%s' % watch_plugin
        ])
    if dev:
        buildCommand.append('--env=dev')
    else:
        buildCommand.append('--env=prod')
    check_call(buildCommand, cwd=staging)


def _collectPluginDependencies():
    packages = {}
    for pluginName in allPlugins():
        plugin = getPlugin(pluginName)
        packages.update(plugin.npmPackages())
    return packages


def _generatePackageJSON(staging, source):
    with open(source, 'r') as f:
        sourceJSON = json.load(f)
    deps = sourceJSON['dependencies']
    deps['@girder/core'] = 'file:%s' % os.path.join(os.path.dirname(source), 'src')
    plugins = _collectPluginDependencies()
    deps.update(plugins)
    sourceJSON['girder'] = {
        'plugins': list(plugins.keys())
    }
    with open(os.path.join(staging, 'package.json'), 'w') as f:
        json.dump(sourceJSON, f)
